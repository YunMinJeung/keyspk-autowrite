"""
글감 생성 모듈
키워드를 입력받아 제목, 아웃라인, 썸네일 프롬프트를 생성합니다.
OpenAI API를 사용하여 동적으로 생성합니다.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import requests

# 환경 변수 로드
load_dotenv()

# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv('Perplexity_API_KEY')

def get_tone_prompt(tone):
    """톤별 시스템 프롬프트 반환"""
    tone_prompts = {
        'informative': "당신은 객관적이고 전문적인 정보를 전달하는 전문가입니다. 신뢰할 수 있고 정확한 정보 제공에 중점을 둡니다.",
        'review': "당신은 개인 경험과 솔직한 후기를 바탕으로 실용적인 조언을 제공하는 리뷰어입니다. 장단점을 균형있게 다룹니다.",
        'friendly': "당신은 친구에게 설명하듯 편안하고 친근한 말투로 쉽게 이해할 수 있도록 설명하는 가이드입니다.",
        'expert': "당신은 해당 분야의 깊은 전문 지식을 가진 전문가로서 심도 있는 분석과 인사이트를 제공합니다.",
        'storytelling': "당신은 이야기를 통해 독자의 흥미를 끌고 몰입감 있게 정보를 전달하는 스토리텔러입니다.",
        'comparison': "당신은 여러 옵션을 체계적으로 비교 분석하여 독자의 선택을 돕는 분석 전문가입니다."
    }
    return tone_prompts.get(tone, tone_prompts['informative'])

def get_tone_description(tone):
    """톤별 설명 반환"""
    tone_descriptions = {
        'informative': "객관적이고 신뢰할 수 있는 정보 전달 중심",
        'review': "실제 경험 바탕의 솔직한 후기와 평가",
        'friendly': "친구처럼 편안하고 이해하기 쉬운 설명",
        'expert': "전문가 수준의 깊이 있는 분석과 인사이트",
        'storytelling': "흥미롭고 몰입감 있는 스토리텔링",
        'comparison': "체계적인 비교 분석을 통한 선택 가이드"
    }
    return tone_descriptions.get(tone, tone_descriptions['informative'])

def generate_titles(keyword, tone='informative'):
    """키워드와 톤 기반으로 제목 5개 생성"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        tone_prompt = get_tone_prompt(tone)
        tone_desc = get_tone_description(tone)
        
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # GPT-4.1 Nano 모델로 변경
            messages=[
                {
                    "role": "system",
                    "content": f"{tone_prompt} SEO 최적화된 블로그 제목을 만들어주세요. 선택된 톤: {tone_desc}"
                },
                {
                    "role": "user",
                    "content": f"""키워드: "{keyword}"
톤/문체: {tone_desc}

다음 조건에 맞는 블로그 제목 5개를 생성해주세요:
1. SEO 최적화 (키워드 포함)
2. 클릭률을 높이는 매력적인 제목
3. 자연스럽고 시의성 있는 내용 (연도 언급 금지)
4. 선택된 톤/문체({tone_desc})에 맞는 스타일
5. 다양한 접근법 (가이드형, 추천형, 비교형, 경험담형, 분석형)

주의사항: 제목에 특정 연도(2022, 2023, 2024, 2025 등)를 넣지 마세요.

JSON 형식으로 응답해주세요:
{{"titles": ["제목1", "제목2", "제목3", "제목4", "제목5"]}}"""
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        titles = result.get('titles', [])
        
        print(f"[글감 생성] OpenAI로 제목 {len(titles)}개 생성 완료")
        return titles
        
    except Exception as e:
        print(f"[generate_titles] OpenAI API 오류: {e}")
        # fallback 제목들
        return [
            f"{keyword} 완벽 가이드 - 2025년 최신 정보 총정리",
            f"초보자를 위한 {keyword} 추천 TOP 5 (실제 사용 후기)",
            f"{keyword}, 이것만 알면 충분! 전문가가 알려주는 핵심 포인트",
            f"2025년 {keyword} 트렌드와 선택 기준 완벽 분석",
            f"하루 만에 마스터하는 {keyword} 활용법 (단계별 가이드)"
        ]

def generate_content_plan(keyword, tone='informative'):
    """Perplexity API를 사용해서 키워드 관련 최신 정보를 수집하고 콘텐츠 기획"""
    try:
        print(f"[콘텐츠 기획] Perplexity API로 '{keyword}' 정보 수집 시작")
        
        if not PERPLEXITY_API_KEY:
            print("[콘텐츠 기획] Perplexity API 키가 없어서 기본 아웃라인으로 대체")
            return generate_fallback_outline(keyword)
        
        # Perplexity API 호출
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 검색 쿼리 생성 - 최신 정보에 중점
        search_query = f"{keyword} 최신 정보 현황 동향 방법 가이드 2025"
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": """당신은 전문적인 콘텐츠 기획자입니다. 키워드에 대한 정보를 수집하고 체계적으로 정리해주세요.

원칙:
- 해당 주제에 가장 적합한 구조로 정리
- 실용적이고 구체적인 내용 위주  
- 마크다운 형식으로 깔끔하게 정리
- 중복 없이 간결하면서도 충분한 정보 제공"""
                },
                {
                    "role": "user", 
                    "content": f"""'{keyword}'에 대한 정보를 조사해서 콘텐츠 기획 자료로 정리해주세요.

이 주제에 가장 적합한 구조로 정리하되, 다음 중에서 필요한 요소들을 포함해주세요:
- 기본 개념과 정의 (필요한 경우)
- 종류나 분류 (여러 옵션이 있는 경우)
- 방법이나 절차 (실행이 필요한 경우)
- 장단점이나 특징 (비교가 필요한 경우)
- 선택 기준이나 조건 (결정이 필요한 경우)
- 주의사항이나 팁 (실용적 조언이 필요한 경우)
- 최신 동향이나 변화 (시의성이 중요한 경우)

해당 주제의 특성에 맞는 구조로 자유롭게 구성하고, 실제 블로그 글 작성에 도움이 되는 구체적이고 정확한 정보를 제공해주세요."""
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content_plan = result['choices'][0]['message']['content']
            
            print(f"[콘텐츠 기획] Perplexity API 성공 - {len(content_plan)}자 수집")
            
            return {
                "type": "content_plan",
                "content": content_plan,
                "keyword": keyword,
                "tone": tone,
                "source": "perplexity"
            }
        else:
            print(f"[콘텐츠 기획] Perplexity API 오류: {response.status_code}")
            print(f"응답: {response.text}")
            return generate_fallback_outline(keyword)
            
    except Exception as e:
        print(f"[콘텐츠 기획] 오류: {e}")
        return generate_fallback_outline(keyword)

def generate_fallback_outline(keyword):
    """Perplexity API 실패 시 사용할 기본 아웃라인"""
    return [
        {
            "title": f"{keyword}란 무엇인가?",
            "subsections": [
                "기본 개념과 정의",
                "왜 중요한가?",
                "현재 시장 상황"
            ]
        },
        {
            "title": f"{keyword} 선택 기준",
            "subsections": [
                "핵심 체크포인트",
                "가격대별 비교",
                "브랜드별 특징"
            ]
        },
        {
            "title": f"추천 {keyword} TOP 5",
            "subsections": [
                "1위: 가성비 최고 제품",
                "2위: 프리미엄 제품",
                "3위: 초보자용 제품"
            ]
        },
        {
            "title": f"{keyword} 활용 팁",
            "subsections": [
                "초보자가 알아야 할 것들",
                "고급 활용법",
                "주의사항과 문제 해결"
            ]
        },
        {
            "title": "결론 및 추천사항",
            "subsections": [
                "상황별 추천",
                "구매 전 마지막 체크리스트",
                "자주 묻는 질문"
            ]
        }
    ]

def generate_thumbnail_prompts(keyword, tone='informative'):
    """키워드와 톤 기반으로 썸네일 프롬프트 3개 생성"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        tone_desc = get_tone_description(tone)
        
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # GPT-4.1 Nano 모델로 변경
            messages=[
                {
                    "role": "system",
                    "content": f"당신은 블로그 썸네일용 이미지 프롬프트를 만드는 전문가입니다. 선택된 톤({tone_desc})에 맞는 시각적 스타일을 고려해주세요."
                },
                {
                    "role": "user",
                    "content": f"""키워드: "{keyword}"
톤/문체: {tone_desc}

이 키워드의 블로그 썸네일로 사용할 이미지 프롬프트 3개를 만들어주세요:
1. 전문적이고 깔끔한 스타일
2. 라이프스타일 중심의 자연스러운 스타일  
3. 선택된 톤({tone_desc})에 특화된 창의적 스타일

각 프롬프트는:
- 구체적인 시각적 요소 포함
- 조명, 구도, 색감 등 세부사항 명시
- 선택된 톤의 분위기 반영
- 실제 사진 촬영 가능한 현실적인 내용
- 한 문장으로 간결하게 작성

JSON 형식으로 응답해주세요:
{{"thumbnails": ["프롬프트1", "프롬프트2", "프롬프트3"]}}"""
                }
            ],
            temperature=0.8,
            max_tokens=400
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            thumbnails = result.get('thumbnails', [])
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 응답을 그대로 사용
            content = response.choices[0].message.content
            print(f"[generate_thumbnail_prompts] JSON 파싱 실패, 원본 응답: {content}")
            # 간단한 텍스트 파싱 시도
            thumbnails = [content] if content else []
        
        # 빈 배열이거나 문제가 있으면 fallback 사용
        if not thumbnails or len(thumbnails) == 0:
            print(f"[generate_thumbnail_prompts] 결과가 비어있음, fallback 사용")
            thumbnails = [
                f"깔끔한 책상 위에 {keyword}가 놓여있고, 따뜻한 조명이 비치는 모습. 미니멀하고 전문적인 느낌의 상품 사진 스타일",
                f"{keyword}를 사용하는 사람의 모습을 측면에서 촬영한 라이프스타일 사진. 자연광이 들어오는 밝은 실내 배경",
                f"여러 개의 {keyword}를 깔끔하게 정렬해서 위에서 내려다본 플랫레이 구도. 흰색 배경에 그림자가 살짝 보이는 스튜디오 촬영 스타일"
            ]
        
        print(f"[글감 생성] OpenAI로 썸네일 프롬프트 {len(thumbnails)}개 생성 완료")
        return thumbnails
        
    except Exception as e:
        print(f"[generate_thumbnail_prompts] OpenAI API 오류: {e}")
        # fallback 썸네일 프롬프트
        return [
            f"깔끔한 책상 위에 {keyword}가 놓여있고, 따뜻한 조명이 비치는 모습. 미니멀하고 전문적인 느낌의 상품 사진 스타일",
            f"{keyword}를 사용하는 사람의 모습을 측면에서 촬영한 라이프스타일 사진. 자연광이 들어오는 밝은 실내 배경",
            f"여러 개의 {keyword}를 깔끔하게 정렬해서 위에서 내려다본 플랫레이 구도. 흰색 배경에 그림자가 살짝 보이는 스튜디오 촬영 스타일"
        ]

def generate_all_topics(keyword, tone='informative'):
    """모든 글감 요소를 한 번에 생성 (톤 포함)"""
    try:
        print(f"[글감 생성] 키워드 '{keyword}', 톤 '{tone}' 처리 시작")
        
        # 각 요소별 생성
        titles = generate_titles(keyword, tone)  # OpenAI 사용
        content_plan = generate_content_plan(keyword, tone)  # Perplexity 사용
        thumbnails = generate_thumbnail_prompts(keyword, tone)  # OpenAI 사용
        
        result = {
            'keyword': keyword,
            'tone': tone,
            'titles': titles,
            'contentPlan': content_plan,  # outline 대신 contentPlan 사용
            'thumbnails': thumbnails
        }
        
        print(f"[글감 생성] 완료 - 제목: {len(titles)}개, 콘텐츠 기획: 완료, 썸네일: {len(thumbnails)}개")
        return result
        
    except Exception as e:
        print(f"[generate_all_topics] 오류: {e}")
        return {
            'keyword': keyword,
            'tone': tone,
            'titles': [f"{keyword} 관련 글"],
            'contentPlan': {"type": "content_plan", "content": f"{keyword}에 대한 기본 정보입니다.", "source": "fallback"},
            'thumbnails': [f"{keyword} 이미지"]
        }
