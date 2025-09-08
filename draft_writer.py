"""
전체글 완성 모듈
글감 생성에서 받은 데이터를 바탕으로 완전한 블로그 글을 작성합니다.
Claude API를 사용하여 고품질 콘텐츠를 생성합니다.
실시간 스트리밍 기능 포함.
"""

import anthropic
import os
from dotenv import load_dotenv
import json
import re

# 환경 변수 로드
load_dotenv()
# Claude client는 함수 내부에서 각각 생성

def get_tone_writing_style(tone):
    """톤별 글쓰기 스타일 가이드 반환"""
    tone_styles = {
        'informative': {
            'style': "객관적이고 정확한 정보를 체계적으로 전달하는 스타일",
            'reader': "정보를 찾는 일반 독자",
            'approach': "전문 용어를 적절히 사용하되 이해하기 쉽게 설명"
        },
        'review': {
            'style': "개인 경험을 바탕으로 솔직하고 구체적인 후기를 작성하는 스타일", 
            'reader': "구매나 선택을 고민하는 독자",
            'approach': "장단점을 균형있게 다루고 실용적인 조언 제공"
        },
        'friendly': {
            'style': "친구에게 말하듯 친근하고 편안한 말투",
            'reader': "초보자나 일반인",
            'approach': "어려운 내용도 쉽게 풀어서 설명하고 공감대 형성"
        },
        'expert': {
            'style': "전문가 수준의 깊이 있는 분석과 인사이트",
            'reader': "해당 분야의 전문가나 심화 학습자",
            'approach': "근거를 제시하고 논리적으로 설명하는 권위 있는 톤"
        },
        'storytelling': {
            'style': "이야기 형식으로 흥미롭게 풀어내는 스타일",
            'reader': "재미있고 몰입감 있는 콘텐츠를 원하는 독자",
            'approach': "상황 설정과 감정적 어필을 활용한 스토리텔링"
        },
        'comparison': {
            'style': "여러 옵션을 체계적으로 비교 분석하는 스타일",
            'reader': "선택이나 결정을 위해 비교 정보가 필요한 독자", 
            'approach': "표나 항목별 비교를 통해 명확한 차이점 제시"
        }
    }
    return tone_styles.get(tone, tone_styles['informative'])

def extract_related_keywords(content_plan, keyword):
    """콘텐츠 기획에서 관련 키워드 추출"""
    try:
        if not content_plan or not content_plan.get('content'):
            return []
        
        content = content_plan['content']
        # 간단한 키워드 추출 (실제로는 더 정교한 NLP 처리 가능)
        keywords = []
        
        # 한글 단어 추출 (2-4글자)
        words = re.findall(r'[가-힣]{2,4}', content)
        word_freq = {}
        
        for word in words:
            if word != keyword and len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도수 기준 상위 5개
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:5] if freq >= 2]
        
        return keywords[:3]  # 최대 3개만
    except:
        return []

def generate_meta_description(title, keyword, content_preview):
    """SEO용 메타 디스크립션 생성"""
    try:
        # 제목과 키워드를 조합해서 간단한 메타 디스크립션 생성
        description = f"{keyword}에 대한 완벽 가이드. {title[:50]}... 자세한 정보와 실용적인 팁을 확인하세요."
        return description[:150]  # 메타 디스크립션은 보통 150자 이내
    except:
        return f"{keyword}에 대한 상세한 정보와 가이드를 제공합니다."

def generate_full_article(keyword, title, content_plan, tone='informative', thumbnails=None):
    """Claude API를 사용해서 전체 블로그 글을 생성"""
    try:
        print(f"[전체글 생성] Claude API로 키워드: '{keyword}', 제목: '{title}', 톤: '{tone}' 처리 시작")
        
        # Claude API 키 확인
        api_key = os.getenv('Claude_API_KEY')
        if not api_key:
            raise Exception("Claude API 키가 설정되지 않았습니다")
        
        print(f"[디버그] Claude API 키 확인: {'설정됨' if api_key else '없음'}")
        print(f"[디버그] Content Plan 타입: {type(content_plan)}")
        print(f"[디버그] Content Plan 내용: {str(content_plan)[:200]}...")
        
        tone_info = get_tone_writing_style(tone)
        
        # 콘텐츠 기획 데이터 처리
        if isinstance(content_plan, dict) and content_plan.get('type') == 'content_plan':
            source_content = content_plan.get('content', '')
        elif isinstance(content_plan, list):
            # 기존 아웃라인 형식 처리
            source_content = ""
            for i, section in enumerate(content_plan, 1):
                source_content += f"{i}. {section.get('title', '')}\n"
                if section.get('subsections'):
                    for j, subsection in enumerate(section['subsections'], 1):
                        source_content += f"  {i}.{j} {subsection}\n"
        else:
            source_content = str(content_plan) if content_plan else ""
        
        print(f"[디버그] 처리된 소스 콘텐츠 길이: {len(source_content)}")
        
        # 관련 키워드 추출
        related_keywords = extract_related_keywords(content_plan, keyword)
        
        # Claude API 클라이언트 초기화 확인
        try:
            claude_client = anthropic.Anthropic(api_key=api_key)
            print("[디버그] Claude 클라이언트 초기화 성공")
        except Exception as e:
            print(f"[디버그] Claude 클라이언트 초기화 실패: {e}")
            raise e
        
        # 재시도 로직 추가
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[디버그] Claude API 요청 시작 (시도 {attempt + 1}/{max_retries})")
                response = claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,  # 토큰 수 증가
                    messages=[
                    {
                        "role": "user",
                        "content": f"""당신은 SEO 최적화와 사용자 친화적인 글쓰기 전문가입니다.

**중요: 절대로 내용을 생략하지 말고 완전한 블로그 글을 작성해주세요. "[이하 생략]"이나 "[나머지 내용...]" 같은 표현은 절대 사용하지 마세요.**

**절대 중단하지 마세요! 다음과 같은 표현들을 사용하지 마세요:**
- "[계속해서 나머지 섹션들도 이어서 작성하시겠습니까?]"
- "[이어서 작성할까요?]"
- "[나머지 내용을 원하시면...]"
- "[...더 자세한 내용이 필요하시면...]"
- "[시간 관계상 여기서 마무리하겠습니다]"
- "[다음 섹션으로 계속...]"
- "[계속...]"
- "[이어서...]"
- "[...생략...]"
- "[더 보기]"

**반드시 완전한 글을 한 번에 끝까지 작성하세요. 중간에 멈추거나 확인을 요청하지 마세요.**

**당신의 임무는 완전한 블로그 글을 작성하는 것입니다. 절대로 요약하거나 생략하지 말고, 모든 섹션을 완성된 형태로 작성하세요.**

**이것은 요약이 아닌 완전한 블로그 글입니다. 각 주제를 깊이 있게 다루고, 독자가 완전히 이해할 수 있도록 자세히 설명해주세요.**

**절대 요약하지 마세요! 다음과 같이 상세하게 작성해주세요:**
- 각 H2 섹션은 반드시 800-1000자 분량으로 작성
- 각 H3 하위 섹션도 300-400자 분량으로 상세 작성
- 단순 나열이 아닌 완전한 문단으로 구성
- 구체적인 예시, 경험담, 비교, 분석 포함
- 독자의 궁금증을 완전히 해결하는 깊이 있는 설명
- "입니다", "습니다" 같은 완전한 문장으로 작성

**작성 조건:**
- 키워드: "{keyword}"
- 제목: "{title}"
- 글의 톤/문체: {tone} ({tone_info['style']})
- 독자 대상: {tone_info['reader']}

**주어진 소스 정보:**
{source_content}

**글 작성 요구사항:**
1. **완전한 글 작성**: 모든 내용을 빠짐없이 작성하고 생략하지 마세요
2. **최소 5000자 이상**: 충분히 상세하고 깊이 있는 내용으로 작성
3. **각 섹션 상세화**: 각 H2 섹션마다 최소 3-4개 문단으로 구성
4. **구체적인 설명**: 단순 나열이 아닌 자세한 설명과 근거 제시
5. **실전 경험**: 구체적인 사례, 경험담, 단계별 가이드 포함
6. **SEO 최적화**: 키워드를 자연스럽게 본문에 5-8회 포함
7. **가독성**: 쉽고 친근한 설명, 구체적 예시 사용
8. **실용성**: 독자에게 실제로 도움이 되는 구체적인 정보 제공

**구조 요구사항:**
- H2(##), H3(###) 제목 구조 사용
- 각 H2 섹션마다 충분한 설명 (최소 4-5문단, 400-600자)
- 각 H3 하위 섹션도 2-3문단으로 상세 작성
- 단순 나열이 아닌 스토리텔링과 구체적 설명
- 실용적인 팁과 구체적인 정보 포함
- 독자의 궁금증을 완전히 해결하는 깊이 있는 내용

**반드시 포함할 내용:**
- 소스에서 언급된 모든 주요 정보를 빠짐없이 상세히 설명
- 각 항목별 구체적인 특징, 방법, 조건 등
- 실용적인 팁과 주의사항

**글쓰기 스타일:**
- 각 문단은 최소 3-4문장으로 구성
- 구체적인 수치, 데이터, 예시 포함
- "왜 그런지", "어떻게 하는지" 상세한 설명
- 독자의 궁금증을 해결하는 내용

**글쓰기 스타일 가이드:**
- 각 문단은 최소 3-4문장으로 구성
- 구체적인 수치, 데이터, 예시 포함
- "왜 그런지", "어떻게 하는지" 상세한 설명
- 독자가 실제로 적용할 수 있는 구체적인 방법 제시
- 비교, 분석, 경험담을 통한 깊이 있는 내용

**글 끝 요소:**
- 핵심 내용 요약
- 행동 유도(CTA)
- 관련 키워드: {', '.join(related_keywords) if related_keywords else keyword + ' 관련'}
- 추천 태그 (#태그 형식 5-8개)

**다시 강조: 절대로 "[이하 생략]", "[나머지 내용]", "..." 등으로 내용을 줄이지 말고, 모든 캠핑장과 정보를 완전히 작성해주세요.**

{tone_info['approach']} 방식으로 완전한 글을 작성해주세요.

**마지막 확인: 모든 섹션을 완성하고, 요약부터 태그까지 포함해서 완전한 블로그 글을 한 번에 끝까지 작성하세요. 절대로 중간에 멈추지 마세요.**

**글 작성 완료 기준:**
1. 모든 H2 섹션이 완성되어야 함
2. 요약/결론 섹션 포함
3. CTA(행동 유도) 포함  
4. 관련 키워드 포함
5. 추천 태그 포함
6. 5000자 이상 분량 달성

**이 모든 요소가 포함된 완전한 글을 지금 바로 작성하세요!**"""
                    }
                ]
                )
                print("[디버그] Claude API 응답 받음")
                break  # 성공하면 루프 종료
                
            except anthropic.APIError as e:
                print(f"[디버그] Claude API 오류 (시도 {attempt + 1}): {e}")
                error_message = str(e)
                
                # Overloaded 오류인 경우 재시도
                if "overloaded" in error_message.lower() and attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 2  # 2초, 4초, 6초 대기
                    print(f"[디버그] 서버 과부하, {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[디버그] 오류 타입: {type(e)}")
                    print(f"[디버그] 오류 세부사항: {e.response.text if hasattr(e, 'response') else '응답 없음'}")
                    raise e
            except Exception as e:
                print(f"[디버그] 일반 오류 (시도 {attempt + 1}): {e}")
                if attempt == max_retries - 1:  # 마지막 시도에서도 실패
                    raise e
                else:
                    import time
                    time.sleep(2)  # 2초 대기 후 재시도
                    continue
        
        article_content = response.content[0].text
        
        # 관련 키워드와 메타 디스크립션 생성
        content_preview = article_content[:200]
        meta_description = generate_meta_description(title, keyword, content_preview)
        
        result = {
            'keyword': keyword,
            'title': title,
            'tone': tone,
            'content': article_content,
            'contentPlan': content_plan,
            'thumbnails': thumbnails or [],
            'wordCount': len(article_content.replace(' ', '')),
            'relatedKeywords': related_keywords,
            'metaDescription': meta_description,
            'source': 'claude'
        }
        
        print(f"[전체글 생성] Claude API 완료 - 글자 수: {result['wordCount']:,}자")
        return result
        
    except Exception as e:
        print(f"[전체글 생성] Claude API 오류: {e}")
        return {
            'keyword': keyword,
            'title': title,
            'tone': tone,
            'content': f"# {title}\n\n죄송합니다. 글 생성 중 오류가 발생했습니다.\n\n키워드: {keyword}\n톤: {tone}\n\n오류: {str(e)}",
            'contentPlan': content_plan,
            'thumbnails': thumbnails or [],
            'wordCount': 0,
            'relatedKeywords': [],
            'metaDescription': f"{keyword}에 대한 정보입니다.",
            'error': str(e),
            'source': 'claude_error'
        }

def generate_article_stream(keyword, title, content_plan, tone='informative', thumbnails=None):
    """Claude API를 사용해서 실시간 스트리밍으로 글 생성"""
    try:
        print(f"[스트리밍 글 생성] Claude API로 키워드: '{keyword}', 제목: '{title}', 톤: '{tone}' 처리 시작")
        
        # Claude API 키 확인
        api_key = os.getenv('Claude_API_KEY')
        if not api_key:
            raise Exception("Claude API 키가 설정되지 않았습니다")
        
        claude_client = anthropic.Anthropic(api_key=api_key)
        tone_info = get_tone_writing_style(tone)
        
        # 콘텐츠 기획 데이터 처리 (generate_full_article과 동일)
        if isinstance(content_plan, dict) and content_plan.get('type') == 'content_plan':
            source_content = content_plan.get('content', '')
        elif isinstance(content_plan, list):
            source_content = ""
            for i, section in enumerate(content_plan, 1):
                source_content += f"{i}. {section.get('title', '')}\n"
                if section.get('subsections'):
                    for j, subsection in enumerate(section['subsections'], 1):
                        source_content += f"  {i}.{j} {subsection}\n"
        else:
            source_content = str(content_plan) if content_plan else ""
        
        related_keywords = extract_related_keywords(content_plan, keyword)
        
        # Claude API 스트리밍 요청
        with claude_client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,  # 토큰 수 증가
            messages=[
                {
                    "role": "user", 
                    "content": f"""당신은 SEO 최적화와 사용자 친화적인 글쓰기 전문가입니다.

**중요: 절대로 내용을 생략하지 말고 완전한 블로그 글을 작성해주세요. "[이하 생략]"이나 "[나머지 내용...]" 같은 표현은 절대 사용하지 마세요.**

**절대 중단하지 마세요! 다음과 같은 표현들을 사용하지 마세요:**
- "[계속해서 나머지 섹션들도 이어서 작성하시겠습니까?]"
- "[이어서 작성할까요?]"
- "[나머지 내용을 원하시면...]"
- "[...더 자세한 내용이 필요하시면...]"
- "[시간 관계상 여기서 마무리하겠습니다]"
- "[다음 섹션으로 계속...]"
- "[계속...]"
- "[이어서...]"
- "[...생략...]"
- "[더 보기]"

**반드시 완전한 글을 한 번에 끝까지 작성하세요. 중간에 멈추거나 확인을 요청하지 마세요.**

**당신의 임무는 완전한 블로그 글을 작성하는 것입니다. 절대로 요약하거나 생략하지 말고, 모든 섹션을 완성된 형태로 작성하세요.**

**이것은 요약이 아닌 완전한 블로그 글입니다. 각 주제를 깊이 있게 다루고, 독자가 완전히 이해할 수 있도록 자세히 설명해주세요.**

**절대 요약하지 마세요! 다음과 같이 상세하게 작성해주세요:**
- 각 H2 섹션은 반드시 800-1000자 분량으로 작성
- 각 H3 하위 섹션도 300-400자 분량으로 상세 작성
- 단순 나열이 아닌 완전한 문단으로 구성
- 구체적인 예시, 경험담, 비교, 분석 포함
- 독자의 궁금증을 완전히 해결하는 깊이 있는 설명
- "입니다", "습니다" 같은 완전한 문장으로 작성

**작성 조건:**
- 키워드: "{keyword}"
- 제목: "{title}"
- 글의 톤/문체: {tone} ({tone_info['style']})
- 독자 대상: {tone_info['reader']}

**주어진 소스 정보:**
{source_content}

**글 작성 요구사항:**
1. **완전한 글 작성**: 모든 내용을 빠짐없이 작성하고 생략하지 마세요
2. **최소 5000자 이상**: 충분히 상세하고 깊이 있는 내용으로 작성
3. **각 섹션 상세화**: 각 H2 섹션마다 최소 3-4개 문단으로 구성
4. **구체적인 설명**: 단순 나열이 아닌 자세한 설명과 근거 제시
5. **실전 경험**: 구체적인 사례, 경험담, 단계별 가이드 포함
6. **SEO 최적화**: 키워드 자연스럽게 포함, H2/H3 제목 구조
7. **실용성**: 독자에게 실제로 도움이 되는 구체적인 정보 제공

**반드시 포함할 내용:**
- 소스에서 언급된 모든 주요 정보를 빠짐없이 상세히 설명
- 각 항목별 구체적인 특징, 방법, 조건 등
- 실용적인 팁과 주의사항

**글쓰기 스타일:**
- 각 문단은 최소 3-4문장으로 구성
- 구체적인 수치, 데이터, 예시 포함
- "왜 그런지", "어떻게 하는지" 상세한 설명

**글 끝 요소:**
- 요약, CTA, 관련키워드({', '.join(related_keywords) if related_keywords else keyword}), 추천태그 포함

**다시 강조: 절대로 생략하지 말고 완전한 글을 작성해주세요.**

{tone_info['approach']} 방식으로 작성해주세요.

**마지막 확인: 모든 섹션을 완성하고, 요약부터 태그까지 포함해서 완전한 블로그 글을 한 번에 끝까지 작성하세요. 절대로 중간에 멈추지 마세요.**

**글 작성 완료 기준:**
1. 모든 H2 섹션이 완성되어야 함
2. 요약/결론 섹션 포함
3. CTA(행동 유도) 포함  
4. 관련 키워드 포함
5. 추천 태그 포함
6. 5000자 이상 분량 달성

**이 모든 요소가 포함된 완전한 글을 지금 바로 작성하세요!**"""
                }
            ]
        ) as stream:
            for text in stream.text_stream:
                # JSON 형태로 스트리밍 데이터 반환
                yield f"data: {json.dumps({'content': text, 'done': False})}\n\n"
        
        # 완료 신호
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        print(f"[스트리밍 글 생성] Claude API 완료")
        
    except Exception as e:
        print(f"[스트리밍 글 생성] Claude API 오류: {e}")
        error_data = {
            'content': f"\n\n⚠️ 글 생성 중 오류가 발생했습니다: {str(e)}",
            'done': True,
            'error': str(e)
        }
        yield f"data: {json.dumps(error_data)}\n\n"

def regenerate_article(keyword, title, content_plan, tone='informative', thumbnails=None):
    """글을 다시 생성 (다른 접근 방식으로)"""
    try:
        print(f"[글 재생성] Claude API로 키워드: '{keyword}', 제목: '{title}' 처리")
        
        # Claude API 키 확인
        api_key = os.getenv('Claude_API_KEY')
        if not api_key:
            raise Exception("Claude API 키가 설정되지 않았습니다")
        
        claude_client = anthropic.Anthropic(api_key=api_key)
        tone_info = get_tone_writing_style(tone)
        
        # 콘텐츠 기획 데이터 처리
        if isinstance(content_plan, dict) and content_plan.get('type') == 'content_plan':
            source_content = content_plan.get('content', '')
        elif isinstance(content_plan, list):
            source_content = ""
            for i, section in enumerate(content_plan, 1):
                source_content += f"{i}. {section.get('title', '')}\n"
                if section.get('subsections'):
                    for j, subsection in enumerate(section['subsections'], 1):
                        source_content += f"  {i}.{j} {subsection}\n"
        else:
            source_content = str(content_plan) if content_plan else ""
        
        related_keywords = extract_related_keywords(content_plan, keyword)
        
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,  # 토큰 수 증가
            messages=[
                {
                    "role": "user",
                    "content": f"""당신은 SEO 최적화와 사용자 친화적인 글쓰기 전문가입니다. 이전과는 다른 새로운 접근 방식으로 글을 작성해주세요.

**중요: 절대로 내용을 생략하지 말고 완전한 블로그 글을 작성해주세요. "[이하 생략]"이나 "[나머지 내용...]" 같은 표현은 절대 사용하지 마세요.**

**절대 중단하지 마세요! 다음과 같은 표현들을 사용하지 마세요:**
- "[계속해서 나머지 섹션들도 이어서 작성하시겠습니까?]"
- "[이어서 작성할까요?]"
- "[나머지 내용을 원하시면...]"
- "[...더 자세한 내용이 필요하시면...]"
- "[시간 관계상 여기서 마무리하겠습니다]"
- "[다음 섹션으로 계속...]"
- "[계속...]"
- "[이어서...]"
- "[...생략...]"
- "[더 보기]"

**반드시 완전한 글을 한 번에 끝까지 작성하세요. 중간에 멈추거나 확인을 요청하지 마세요.**

**당신의 임무는 완전한 블로그 글을 작성하는 것입니다. 절대로 요약하거나 생략하지 말고, 모든 섹션을 완성된 형태로 작성하세요.**

**이것은 요약이 아닌 완전한 블로그 글입니다. 각 주제를 깊이 있게 다루고, 독자가 완전히 이해할 수 있도록 자세히 설명해주세요.**

**절대 요약하지 마세요! 다음과 같이 상세하게 작성해주세요:**
- 각 H2 섹션은 반드시 800-1000자 분량으로 작성
- 각 H3 하위 섹션도 300-400자 분량으로 상세 작성
- 단순 나열이 아닌 완전한 문단으로 구성
- 구체적인 예시, 경험담, 비교, 분석 포함
- 독자의 궁금증을 완전히 해결하는 깊이 있는 설명
- "입니다", "습니다" 같은 완전한 문장으로 작성

**작성 조건:**
- 키워드: "{keyword}"
- 제목: "{title}"
- 글의 톤/문체: {tone} ({tone_info['style']})
- 독자 대상: {tone_info['reader']}

**주어진 소스 정보:**
{source_content}

**재생성 요구사항:**
1. **완전한 글 작성**: 모든 내용을 빠짐없이 작성하고 생략하지 마세요
2. **새로운 구성**: 이전과 다른 관점이나 구조로 접근
3. **창의적 표현**: 다른 예시, 비유, 설명 방식 사용  
4. **차별화된 내용**: 같은 정보라도 완전히 다른 방식으로 풀어내기
5. **최소 5000자 이상**: 충분히 상세하고 깊이 있는 내용으로 작성
6. **각 섹션 상세화**: 각 H2 섹션마다 최소 3-4개 문단으로 구성
7. **구체적인 설명**: 단순 나열이 아닌 자세한 설명과 근거 제시

**반드시 포함할 내용:**
- 소스에서 언급된 모든 주요 정보를 빠짐없이 상세히 설명
- 각 항목별 구체적인 특징, 방법, 조건 등

**글 끝 요소**: 요약, CTA, 관련키워드({', '.join(related_keywords) if related_keywords else keyword}), 추천태그

**다시 강조: 절대로 생략하지 말고 완전한 새로운 글을 작성해주세요.**

{tone_info['approach']} 방식으로 이전과는 완전히 다른 새로운 글을 작성해주세요.

**마지막 확인: 모든 섹션을 완성하고, 요약부터 태그까지 포함해서 완전한 블로그 글을 한 번에 끝까지 작성하세요. 절대로 중간에 멈추지 마세요.**

**글 작성 완료 기준:**
1. 모든 H2 섹션이 완성되어야 함
2. 요약/결론 섹션 포함
3. CTA(행동 유도) 포함  
4. 관련 키워드 포함
5. 추천 태그 포함
6. 5000자 이상 분량 달성

**이 모든 요소가 포함된 완전한 글을 지금 바로 작성하세요!**"""
                }
            ]
        )
        
        article_content = response.content[0].text
        
        # 메타 정보 생성
        content_preview = article_content[:200]
        meta_description = generate_meta_description(title, keyword, content_preview)
        
        result = {
            'keyword': keyword,
            'title': title,
            'tone': tone,
            'content': article_content,
            'contentPlan': content_plan,
            'thumbnails': thumbnails or [],
            'wordCount': len(article_content.replace(' ', '')),
            'relatedKeywords': related_keywords,
            'metaDescription': meta_description,
            'source': 'claude_regenerated'
        }
        
        print(f"[글 재생성] Claude API 완료 - 글자 수: {result['wordCount']:,}자")
        return result
        
    except Exception as e:
        print(f"[글 재생성] Claude API 오류: {e}")
        return {
            'keyword': keyword,
            'title': title,
            'tone': tone,
            'content': f"# {title}\n\n죄송합니다. 글 재생성 중 오류가 발생했습니다.\n\n오류: {str(e)}",
            'contentPlan': content_plan,
            'thumbnails': thumbnails or [],
            'wordCount': 0,
            'relatedKeywords': [],
            'metaDescription': f"{keyword} 재생성 글입니다.",
            'error': str(e),
            'source': 'claude_regenerated_error'
        }
