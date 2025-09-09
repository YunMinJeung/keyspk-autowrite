from flask import Flask, request, jsonify, render_template, Response
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from flask_cors import CORS
import time
from signaturehelper import Signature  # 추가
from topic_generator import generate_all_topics  # 글감 생성 모듈 추가
from draft_writer import generate_full_article, regenerate_article, generate_article_stream  # 전체글 완성 모듈 추가
from openai import OpenAI  # 롱테일 키워드용 OpenAI 추가
import json

app = Flask(__name__, static_folder='static')

# CORS 설정
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type"]}})

# 환경 변수 로드
load_dotenv()

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic-generator')
def topic_generator():
    return render_template('topic_generator.html')

@app.route('/draft-writer')
def draft_writer():
    return render_template('draft_writer.html')

@app.route('/api/generate-topics', methods=['POST'])
def generate_topics():
    try:
        data = request.json
        keyword = data.get('keyword')
        tone = data.get('tone', 'informative')  # 기본값은 정보형
        print(f"[글감 생성] 키워드: '{keyword}', 톤: '{tone}'")
        
        if not keyword:
            return jsonify({'error': '키워드가 필요합니다'}), 400

        # topic_generator 모듈 사용 (톤 포함)
        result = generate_all_topics(keyword, tone)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"글감 생성 중 오류: {str(e)}")
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

@app.route('/api/generate-article', methods=['POST'])
def generate_article():
    try:
        data = request.json
        keyword = data.get('keyword')
        title = data.get('title')
        content_plan = data.get('contentPlan')  # outline 대신 contentPlan 사용
        tone = data.get('tone', 'informative')
        thumbnails = data.get('thumbnails', [])
        
        print(f"[전체글 API] 키워드: '{keyword}', 제목: '{title}', 톤: '{tone}'")
        
        if not all([keyword, title, content_plan]):
            return jsonify({'error': '키워드, 제목, 콘텐츠 기획이 필요합니다'}), 400

        # draft_writer 모듈 사용 (Claude API)
        result = generate_full_article(keyword, title, content_plan, tone, thumbnails)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"전체글 생성 중 오류: {str(e)}")
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

@app.route('/api/regenerate-article', methods=['POST'])
def regenerate_article_api():
    try:
        data = request.json
        keyword = data.get('keyword')
        title = data.get('title')
        content_plan = data.get('contentPlan')  # outline 대신 contentPlan 사용
        tone = data.get('tone', 'informative')
        thumbnails = data.get('thumbnails', [])
        
        print(f"[글 재생성 API] 키워드: '{keyword}', 제목: '{title}'")
        
        if not all([keyword, title, content_plan]):
            return jsonify({'error': '키워드, 제목, 콘텐츠 기획이 필요합니다'}), 400

        # draft_writer 모듈 사용 (재생성)
        result = regenerate_article(keyword, title, content_plan, tone, thumbnails)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"글 재생성 중 오류: {str(e)}")
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

@app.route('/api/generate-article-stream', methods=['POST'])
def generate_article_stream_api():
    try:
        print("[스트리밍 API] 요청 받음")
        data = request.json
        print(f"[스트리밍 API] 받은 데이터: {data}")
        print(f"[스트리밍 API] 받은 데이터 키들: {list(data.keys()) if data else 'None'}")
        
        keyword = data.get('keyword')
        title = data.get('title')
        content_plan = data.get('contentPlan')  # outline 대신 contentPlan 사용
        tone = data.get('tone', 'informative')
        thumbnails = data.get('thumbnails', [])
        
        print(f"[스트리밍 API] 키워드: '{keyword}', 제목: '{title}', 톤: '{tone}'")
        print(f"[스트리밍 API] content_plan 타입: {type(content_plan)}")
        print(f"[스트리밍 API] content_plan 존재: {content_plan is not None}")
        
        # outline 키로도 확인해보기
        outline = data.get('outline')
        print(f"[스트리밍 API] outline 키 존재: {outline is not None}")
        print(f"[스트리밍 API] outline 타입: {type(outline)}")
        
        # 실제로 outline으로 데이터가 온다면 contentPlan으로 설정
        if content_plan is None and outline is not None:
            content_plan = outline
            print("[스트리밍 API] outline을 contentPlan으로 변환함")
        
        if not all([keyword, title, content_plan]):
            missing = []
            if not keyword: missing.append('keyword')
            if not title: missing.append('title') 
            if not content_plan: missing.append('contentPlan')
            error_msg = f'누락된 데이터: {", ".join(missing)}'
            print(f"[스트리밍 API] 오류: {error_msg}")
            return jsonify({'error': error_msg}), 400

        print("[스트리밍 API] 데이터 검증 완료, draft_writer 호출 시작")
        
        # 스트리밍 응답 반환
        def generate():
            try:
                print("[스트리밍 API] 제너레이터 시작")
                yield "data: " + json.dumps({'content': '', 'status': 'starting'}) + "\n\n"
                for chunk in generate_article_stream(keyword, title, content_plan, tone, thumbnails):
                    yield chunk
                print("[스트리밍 API] 제너레이터 완료")
            except Exception as gen_error:
                print(f"[스트리밍 API] 제너레이터 오류: {gen_error}")
                yield "data: " + json.dumps({'content': f'오류: {str(gen_error)}', 'error': True}) + "\n\n"
        
        return Response(
            generate(),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    except Exception as e:
        print(f"[스트리밍 API] 메인 오류: {str(e)}")
        import traceback
        print(f"[스트리밍 API] 트레이스백: {traceback.format_exc()}")
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

@app.route('/api/search', methods=['POST'])
def search_keyword():
    print(f"[API 요청] 받음!")
    try:
        data = request.json
        keyword = data.get('keyword')
        print(f"[API 요청] 키워드: '{keyword}'")
        
        if not keyword:
            return jsonify({'error': '키워드가 필요합니다'}), 400

        # 1. 실제 검색량 데이터 시도 (네이버 검색광고 API)
        search_volume_data = get_keyword_search_volume(keyword)
        
        # 2. 검색 트렌드 데이터 가져오기 (3개월)
        today = datetime.now()
        start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        search_trend = get_search_trend_data(keyword, start_date, end_date)

        # 3. 블로그 데이터 가져오기
        blog_total, blog_items = get_blog_data(keyword)
        
        # 4. 카페 데이터 가져오기
        cafe_total, cafe_items = get_cafe_data(keyword)

        # 전체 콘텐츠 수
        total_content_count = blog_total + cafe_total

        # 5. 연관 키워드 데이터 가져오기
        related_keywords_data = get_related_keywords_with_volume(keyword)

        # 6. 롱테일 키워드 생성 (초보자용)
        longtail_keywords = generate_longtail_keywords(keyword)

        # 7. 월간 발행량 추정 (새로 추가)
        monthly_estimates = calculate_all_estimations(search_volume_data, total_content_count, search_trend)
        final_monthly_estimate = get_final_monthly_estimate(search_volume_data, total_content_count, search_trend)

        # 분석 결과 계산 (실제 검색량 우선, 없으면 트렌드 기반)
        if search_volume_data:
            analysis = calculate_real_search_analysis(search_volume_data, total_content_count, search_trend, final_monthly_estimate)
            search_volume_info = search_volume_data
        else:
            analysis = calculate_trend_analysis(search_trend, total_content_count, final_monthly_estimate)
            search_volume_info = None

        # 응답 데이터 구성
        response_data = {
            'keyword': keyword,
            'searchTrend': search_trend,
            'searchVolume': search_volume_info,  # 실제 검색량 (있는 경우)
            'blog': {
                'total': blog_total,
                'recentPosts': blog_items,
                'monthlyEstimate': final_monthly_estimate * 0.6 if final_monthly_estimate else 0  # 블로그 비중 60%
            },
            'cafe': {
                'total': cafe_total,
                'recentPosts': cafe_items,
                'monthlyEstimate': final_monthly_estimate * 0.4 if final_monthly_estimate else 0  # 카페 비중 40%
            },
            'totalContentCount': total_content_count,
            'monthlyEstimates': monthly_estimates,  # 각 추정 방식별 결과
            'finalMonthlyEstimate': final_monthly_estimate,  # 최종 월간 추정치
            'analysis': analysis,
            'relatedKeywords': related_keywords_data['related_keywords'] if related_keywords_data else [],
            'longtailKeywords': longtail_keywords,  # 롱테일 키워드 추가
            'dataType': 'realSearch' if search_volume_data else 'trendOnly'  # 데이터 타입 표시
        }

        return jsonify(response_data)
    
    except Exception as e:
        print(f"API 처리 중 오류: {str(e)}")
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

def get_final_monthly_estimate(search_volume_data, total_content_count, search_trend_data):
    """여러 추정 방식을 가중 평균하여 최종 월간 발행량 계산"""
    try:
        estimates = calculate_all_estimations(search_volume_data, total_content_count, search_trend_data)
        
        # 가중치 설정 (임시값 - 테스트 후 조정 예정)
        weights = {
            "트렌드 가중 평균": 0.4,
            "검색량 비례 방식": 0.3,
            "키워드 성숙도 기반": 0.3,
            "최신 콘텐츠 샘플링": 0.0  # 미구현
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for method, estimate in estimates.items():
            if method in weights and estimate is not None and estimate > 0:
                weight = weights[method]
                weighted_sum += estimate * weight
                total_weight += weight
                print(f"[가중 평균] {method}: {estimate:.1f} (가중치: {weight})")
        
        if total_weight == 0:
            # 모든 추정이 실패한 경우 기본값
            fallback = total_content_count / 60  # 5년 평균
            print(f"[가중 평균] 모든 추정 실패, 기본값 사용: {fallback:.1f}")
            return fallback
        
        final_estimate = weighted_sum / total_weight
        print(f"[가중 평균] 최종 결과: {final_estimate:.1f}")
        
        return round(final_estimate, 1)
        
    except Exception as e:
        print(f"[get_final_monthly_estimate] 오류: {e}")
        return total_content_count / 60  # 기본값

def get_search_trend_data(keyword, start_date, end_date):
    """네이버 데이터랩 API로 검색 트렌드 조회"""
    # 네이버 API용 키워드 전처리 (띄어쓰기 제거)
    api_keyword = keyword.replace(' ', '').strip()
    print(f"[트렌드 API] 원본: '{keyword}' → 처리됨: '{api_keyword}'")
    
    url = 'https://openapi.naver.com/v1/datalab/search'
    headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
        'Content-Type': 'application/json'
    }
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "month",
        "keywordGroups": [
            {"groupName": api_keyword, "keywords": [api_keyword]}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        print(f"데이터랩 API 응답: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            trend_data = data['results'][0]['data']
            
            return {
                'graphData': {
                    'dates': [item['period'][:7] for item in trend_data],
                    'ratios': [item['ratio'] for item in trend_data]
                },
                'latestRatio': trend_data[-1]['ratio'] if trend_data else 0,
                'period': trend_data[-1]['period'] if trend_data else 'N/A'
            }
        else:
            print(f"데이터랩 API 오류: {response.status_code}, {response.text}")
            return {
                'graphData': {'dates': [], 'ratios': []},
                'latestRatio': 0,
                'period': 'N/A'
            }
    except Exception as e:
        print(f"데이터랩 API 호출 오류: {str(e)}")
        return {
            'graphData': {'dates': [], 'ratios': []},
            'latestRatio': 0,
            'period': 'N/A'
        }

def get_blog_data(keyword):
    """네이버 블로그 검색 API"""
    # 네이버 API용 키워드 전처리 (띄어쓰기 제거)
    api_keyword = keyword.replace(' ', '').strip()
    print(f"[블로그 API] 원본: '{keyword}' → 처리됨: '{api_keyword}'")
    
    url = 'https://openapi.naver.com/v1/search/blog.json'
    headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
    }
    params = {
        'query': api_keyword,
        'display': 10,
        'sort': 'sim'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"블로그 API 응답: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            formatted_items = []
            
            for item in items:
                try:
                    # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
                    postdate = item.get('postdate', '')
                    if postdate and len(postdate) == 8:
                        date = f"{postdate[:4]}-{postdate[4:6]}-{postdate[6:8]}"
                    else:
                        date = '날짜 정보 없음'
                        
                    formatted_items.append({
                        'title': item.get('title', '제목 없음'),
                        'description': item.get('description', '설명 없음'),
                        'link': item.get('link', '#'),
                        'date': date
                    })
                except Exception as e:
                    print(f"블로그 아이템 처리 오류: {e}")
                    continue
                    
            return data.get('total', 0), formatted_items
        else:
            print(f"블로그 API 오류: {response.status_code}, {response.text}")
            return 0, []
    except Exception as e:
        print(f"블로그 API 호출 오류: {str(e)}")
        return 0, []

def get_cafe_data(keyword):
    """네이버 카페 검색 API"""
    # 네이버 API용 키워드 전처리 (띄어쓰기 제거)
    api_keyword = keyword.replace(' ', '').strip()
    print(f"[카페 API] 원본: '{keyword}' → 처리됨: '{api_keyword}'")
    
    url = 'https://openapi.naver.com/v1/search/cafearticle.json'
    headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
    }
    params = {
        'query': api_keyword,
        'display': 10,
        'sort': 'sim'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"카페 API 응답: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            formatted_items = []
            
            for item in items:
                try:
                    # 네이버 카페 API의 실제 필드명 확인
                    print(f"카페 아이템 전체 데이터: {item}")  # 디버깅용
                    
                    # 다양한 날짜 필드명 시도
                    datetime_str = (item.get('datetime', '') or 
                                  item.get('postdate', '') or 
                                  item.get('date', '') or 
                                  item.get('pubDate', '') or
                                  item.get('lastBuildDate', ''))
                    
                    print(f"카페 아이템 날짜 원본: '{datetime_str}'")  # 디버깅용
                    
                    if datetime_str:
                        if len(datetime_str) == 8:  # YYYYMMDD 형식
                            date = f"{datetime_str[:4]}-{datetime_str[4:6]}-{datetime_str[6:8]}"
                        elif len(datetime_str) >= 12:  # YYYYMMDDHHMM 또는 더 긴 형식
                            date = f"{datetime_str[:4]}-{datetime_str[4:6]}-{datetime_str[6:8]}"
                        elif 'T' in datetime_str:  # ISO 8601 형식
                            date = datetime_str.split('T')[0]  # 날짜 부분만 추출
                        elif '-' in datetime_str:  # 이미 YYYY-MM-DD 형식
                            date = datetime_str[:10]  # 날짜 부분만
                        else:
                            date = datetime_str  # 원본 그대로
                    else:
                        date = '날짜 정보 없음'
                        
                    formatted_items.append({
                        'title': item.get('title', '제목 없음'),
                        'description': item.get('description', '설명 없음'),
                        'link': item.get('link', '#'),
                        'date': date
                    })
                except Exception as e:
                    print(f"카페 아이템 처리 오류: {e}, 아이템: {item}")
                    continue
                    
            return data.get('total', 0), formatted_items
        else:
            print(f"카페 API 오류: {response.status_code}, {response.text}")
            return 0, []
    except Exception as e:
        print(f"카페 API 호출 오류: {str(e)}")
        return 0, []

def get_keyword_search_volume(keyword):
    """네이버 검색광고 API를 통해 실제 월간 검색량 조회"""
    # 네이버 API용 키워드 전처리 (띄어쓰기 제거)
    api_keyword = keyword.replace(' ', '').strip()
    print(f"[검색량 API] 원본: '{keyword}' → 처리됨: '{api_keyword}'")
    
    # 환경 변수 확인 (실제 .env 파일의 변수명 사용)
    NAVER_AD_API_KEY = os.getenv('NAVER_AD_API_KEY')
    NAVER_AD_SECRET_KEY = os.getenv('NAVER_AD_SECRET_KEY') 
    NAVER_AD_CUSTOMER_ID = os.getenv('NAVER_AD_CUSTOMER_ID')
    
    print(f"API 키 확인: API_KEY={NAVER_AD_API_KEY[:10] if NAVER_AD_API_KEY else 'None'}..., SECRET_KEY={'설정됨' if NAVER_AD_SECRET_KEY else 'None'}, CUSTOMER_ID={NAVER_AD_CUSTOMER_ID}")
    
    if not all([NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID]):
        print("검색광고 API 키가 설정되지 않음. 트렌드 데이터만 사용합니다.")
        return None
    
    try:
        # 네이버 검색광고 API 호출 (시그니처 방식)
        timestamp = str(int(time.time() * 1000))
        method = 'GET'
        uri = '/keywordstool'
        
        print(f"시그니처 생성 전: timestamp={timestamp}, method={method}, uri={uri}")
        print(f"SECRET_KEY 길이: {len(NAVER_AD_SECRET_KEY)}")
        
        try:
            # signaturehelper.py의 Signature 클래스 사용
            signature = Signature.generate(timestamp, method, uri, NAVER_AD_SECRET_KEY)
            print(f"시그니처 생성 성공: {signature[:20]}...")
        except Exception as sig_error:
            print(f"시그니처 생성 오류: {sig_error}")
            # 직접 시그니처 생성으로 fallback
            import hashlib
            import hmac
            import base64
            message = f"{timestamp}.{method}.{uri}"
            hash_obj = hmac.new(bytes(NAVER_AD_SECRET_KEY, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)
            signature = base64.b64encode(hash_obj.digest()).decode("utf-8")
            print(f"직접 시그니처 생성: {signature[:20]}...")
        
        url = 'https://api.searchad.naver.com/keywordstool'
        headers = {
            'X-Timestamp': timestamp,
            'X-API-KEY': NAVER_AD_API_KEY,
            'X-Customer': NAVER_AD_CUSTOMER_ID,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }
        
        print(f"전송할 헤더: {headers}")
        
        params = {
            'hintKeywords': api_keyword,
            'showDetail': '1'
        }
        
        response = requests.get(url, headers=headers, params=params)
        print(f"검색광고 API 응답: {response.status_code}")
        print(f"응답 헤더: {response.headers}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"검색광고 API 응답 데이터: {result}")
            if 'keywordList' in result and result['keywordList']:
                keyword_data = result['keywordList'][0]
                return {
                    'monthlyPcQcCnt': keyword_data.get('monthlyPcQcCnt', 0),
                    'monthlyMobileQcCnt': keyword_data.get('monthlyMobileQcCnt', 0),
                    'monthlyAvePcClkCnt': keyword_data.get('monthlyAvePcClkCnt', 0),
                    'monthlyAveMobileClkCnt': keyword_data.get('monthlyAveMobileClkCnt', 0),
                    'compIdx': keyword_data.get('compIdx', 'N/A')
                }
            else:
                print("검색광고 API: 키워드 데이터가 없습니다.")
                return None
        else:
            print(f"검색광고 API 오류: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"검색광고 API 호출 오류: {str(e)}")
        return None

def calculate_real_search_analysis(search_volume_data, content_count, search_trend_data=None, monthly_estimate=None):
    """실제 검색량 기반 분석 (월간 추정치 사용)"""
    pc_volume = search_volume_data.get('monthlyPcQcCnt', 0) or 0
    mobile_volume = search_volume_data.get('monthlyMobileQcCnt', 0) or 0
    total_volume = pc_volume + mobile_volume
    
    # 월간 추정치 사용 (기존 누적량 대신)
    if monthly_estimate and monthly_estimate > 0:
        monthly_content = monthly_estimate
    else:
        monthly_content = content_count / 60  # 기본값
    
    print(f"[분석] 검색량: {total_volume:,}, 월간발행량: {monthly_content:.1f}")
    
    if content_count == 0:
        return {
            "기회점수": "무한대",
            "등급": "A+",
            "포화지수": "0%",
            "월간검색량": f"{total_volume:,}",
            "PC검색량": f"{pc_volume:,}",
            "모바일검색량": f"{mobile_volume:,}",
            "콘텐츠수": "0개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": "경쟁이 없는 블루오션! 즉시 콘텐츠를 만드세요!"
        }
    
    if total_volume == 0:
        return {
            "기회점수": "0",
            "등급": "N/A",
            "포화지수": "N/A",
            "월간검색량": "0",
            "PC검색량": "0",
            "모바일검색량": "0",
            "콘텐츠수": f"{content_count:,}개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": "검색량이 없습니다."
        }
    
    # 월간 발행량 기반 분석
    opportunity_score = total_volume / monthly_content if monthly_content > 0 else 0
    saturation_rate = (monthly_content / total_volume) * 100 if total_volume > 0 else 0
    
    # 등급 계산
    if opportunity_score >= 10:
        grade = "A+"
        recommendation = "매우 좋은 기회! 월간 발행량 대비 검색량이 높습니다"
    elif opportunity_score >= 5:
        grade = "A"
        recommendation = "좋은 기회입니다. 콘텐츠 제작을 권장합니다"
    elif opportunity_score >= 2:
        grade = "B"
        recommendation = "적당한 기회입니다. 차별화된 콘텐츠로 접근하세요"
    elif opportunity_score >= 1:
        grade = "C"
        recommendation = "경쟁이 있지만 시도해볼 만합니다"
    elif opportunity_score >= 0.5:
        grade = "D"
        recommendation = "치열한 경쟁입니다"
    else:
        grade = "F"
        recommendation = "포화 상태입니다"
    
    return {
        "기회점수": round(opportunity_score, 2),
        "등급": grade,
        "포화지수": f"{saturation_rate:.1f}%",
        "월간검색량": f"{total_volume:,}",
        "PC검색량": f"{pc_volume:,}",
        "모바일검색량": f"{mobile_volume:,}",
        "콘텐츠수": f"{content_count:,}개",
        "월간발행량": f"{monthly_content:.0f}",
        "추천사항": recommendation
    }

def calculate_trend_analysis(search_trend_data, content_count, monthly_estimate=None):
    """트렌드 기반 분석 (월간 추정치 사용)"""
    # 기본값 설정
    if content_count is None:
        content_count = 0
    content_count = int(content_count) if content_count else 0
    
    # 트렌드 비율 가져오기
    if search_trend_data and search_trend_data.get('latestRatio'):
        trend_ratio = search_trend_data['latestRatio']
    else:
        trend_ratio = 0
    
    # 월간 추정치 사용
    if monthly_estimate and monthly_estimate > 0:
        monthly_content = monthly_estimate
    else:
        monthly_content = content_count / 60  # 기본값
    
    print(f"[분석] 트렌드: {trend_ratio}%, 월간발행량: {monthly_content:.1f}")
    
    # 콘텐츠가 없는 경우
    if content_count == 0:
        return {
            "기회점수": "무한대" if trend_ratio > 0 else "데이터 부족",
            "등급": "A+" if trend_ratio > 0 else "N/A",
            "포화지수": "0%",
            "트렌드비율": f"{trend_ratio}%",
            "콘텐츠수": "0개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": "경쟁이 없는 블루오션! 즉시 콘텐츠를 만드세요!" if trend_ratio > 0 else "검색 트렌드 데이터가 부족합니다."
        }
    
    # 트렌드가 없는 경우
    if trend_ratio == 0:
        return {
            "기회점수": "0",
            "등급": "N/A", 
            "포화지수": "N/A",
            "트렌드비율": "0%",
            "콘텐츠수": f"{content_count:,}개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": "검색 트렌드가 낮거나 데이터를 가져올 수 없습니다."
        }
    
    try:
        # 로그 스케일 기반 분석 (월간 추정치 사용)
        import math
        
        # 월간 발행량 밀도 지수
        content_density = math.log10(max(monthly_content, 1))
        trend_strength = trend_ratio / 10
        
        # 기회점수 계산
        opportunity_score = (trend_strength / max(content_density, 1)) * 10
        
        # 포화지수 계산
        saturation_rate = (content_density / max(trend_strength, 0.1)) * 20
        
        # 등급 계산
        if opportunity_score >= 20:
            grade = "A+"
            recommendation = "매우 좋은 기회! 트렌드 대비 월간 발행량이 적습니다"
        elif opportunity_score >= 15:
            grade = "A"
            recommendation = "좋은 기회입니다. 콘텐츠 제작을 권장합니다"
        elif opportunity_score >= 10:
            grade = "B"
            recommendation = "적당한 기회입니다. 차별화된 콘텐츠로 접근하세요"
        elif opportunity_score >= 6:
            grade = "C"
            recommendation = "경쟁이 있지만 시도해볼 만합니다"
        elif opportunity_score >= 3:
            grade = "D"
            recommendation = "치열한 경쟁. 매우 독창적인 콘텐츠가 필요합니다"
        else:
            grade = "F"
            recommendation = "포화 상태. 다른 키워드를 고려해보세요"
        
        # 포화지수가 100%를 넘지 않도록 제한
        saturation_rate = min(saturation_rate, 100)
        
        return {
            "기회점수": round(opportunity_score, 2),
            "등급": grade,
            "포화지수": f"{saturation_rate:.1f}%",
            "트렌드비율": f"{trend_ratio}%",
            "콘텐츠수": f"{content_count:,}개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": recommendation,
            "상세정보": f"트렌드: {trend_ratio}%, 월간발행량: {monthly_content:.0f}"
        }
        
    except Exception as e:
        print(f"분석 계산 중 오류: {str(e)}")
        return {
            "기회점수": "오류",
            "등급": "N/A",
            "포화지수": "오류",
            "트렌드비율": f"{trend_ratio}%",
            "콘텐츠수": f"{content_count:,}개",
            "월간발행량": f"{monthly_content:.0f}",
            "추천사항": "계산 중 오류가 발생했습니다."
        }

def estimate_by_volume_ratio(search_volume_data, ratio_constant=50):
    """검색량 비례 방식으로 월간 콘텐츠 발행량 추정"""
    try:
        if not search_volume_data:
            return 0

        # PC와 모바일 검색량 합산
        total_volume = search_volume_data.get('monthlyPcQcCnt', 0) + search_volume_data.get('monthlyMobileQcCnt', 0)
        
        if total_volume <= 0:
            return 0

        # 검색량 / 비율 상수
        monthly_estimate = total_volume / ratio_constant
        
        # 최소값 1 설정 (0 미만 방지)
        return max(monthly_estimate, 1)
    except Exception as e:
        print(f"[estimate_by_volume_ratio] 오류: {e}")
        return 0

def estimate_by_keyword_lifecycle(total_content_count, min_months=12, max_months=72):
    """키워드 성숙도 기반 월간 발행량 추정"""
    try:
        if not total_content_count or total_content_count <= 0:
            return 0

        # 콘텐츠 수에 따른 가중치 계산 (12개월 ~ 72개월)
        if total_content_count < 100000:  # 초기
            months = max_months
        elif total_content_count < 1000000:  # 중기
            months = (max_months + min_months) / 2
        else:  # 후기
            months = min_months

        # 월간 발행량 계산
        monthly_estimate = total_content_count / months
        
        return round(monthly_estimate, 1)
    except Exception as e:
        print(f"[estimate_by_keyword_lifecycle] 오류: {e}")
        return 0

def calculate_trend_weighted_monthly(search_trend_data, total_content_count):
    """트렌드 가중 평균 방식으로 월간 콘텐츠 발행량 추정"""
    try:
        if not search_trend_data or not search_trend_data.get('graphData'):
            return total_content_count / 60  # 기본값: 5년 평균
        
        ratios = search_trend_data['graphData']['ratios']
        if not ratios or len(ratios) == 0:
            return total_content_count / 60
        
        # 최근 3개월 트렌드 비율
        recent_ratios = ratios[-3:] if len(ratios) >= 3 else ratios
        current_trend = sum(recent_ratios) / len(recent_ratios)
        
        # 전체 기간 평균 트렌드
        average_trend = sum(ratios) / len(ratios)
        
        # 트렌드 가중치 계산
        if average_trend > 0:
            trend_weight = current_trend / average_trend
        else:
            trend_weight = 1.0
            
        # 기본 추정 기간 (키워드 성숙도에 따라)
        if total_content_count < 100000:  # 10만개 미만: 신생
            base_months = 24
        elif total_content_count < 500000:  # 50만개 미만: 중간
            base_months = 48
        else:  # 50만개 이상: 성숙
            base_months = 72

        # 가중치 적용
        effective_months = base_months * trend_weight
        
        # 최소 12개월, 최대 72개월 제한
        effective_months = max(12, min(72, effective_months))
        
        # 월간 발행량 계산
        monthly_estimate = total_content_count / effective_months
        
        print(f"트렌드 가중 계산: 현재추세={current_trend:.1f}, 평균추세={average_trend:.1f}, 가중치={trend_weight:.2f}, 유효기간={effective_months:.1f}개월, 추정={monthly_estimate:.0f}")
        
        return max(monthly_estimate, 0)  # 음수 방지
    except Exception as e:
        print(f"[calculate_trend_weighted_monthly] 오류: {e}")
        return total_content_count / 60  # 기본값: 5년 평균

def calculate_all_estimations(search_volume_data, total_content_count, search_trend_data):
    """4가지 방식의 월간 발행량 예측 결과를 dict로 반환"""
    try:
        results = {}

        # 각 방식별로 예외 처리
        try:
            # 1. 트렌드 가중 평균 방식
            results["트렌드 가중 평균"] = round(
                calculate_trend_weighted_monthly(search_trend_data, total_content_count), 1
            )
        except Exception as e:
            print(f"[트렌드 가중 평균 계산 오류] {e}")
            results["트렌드 가중 평균"] = None

        try:
            # 2. 검색량 비례 방식
            results["검색량 비례 방식"] = round(estimate_by_volume_ratio(search_volume_data), 1)
        except Exception as e:
            print(f"[검색량 비례 계산 오류] {e}")
            results["검색량 비례 방식"] = None

        # 3. 콘텐츠 날짜 기반 방식 (아직 미구현)
        results["최신 콘텐츠 샘플링"] = None  # 추후 구현 예정

        try:
            # 4. 키워드 성숙도 기반 방식
            results["키워드 성숙도 기반"] = round(estimate_by_keyword_lifecycle(total_content_count), 1)
        except Exception as e:
            print(f"[키워드 성숙도 계산 오류] {e}")
            results["키워드 성숙도 기반"] = None

        # 디버깅용 출력
        print(f"[calculate_all_estimations] 결과:")
        for method, value in results.items():
            if value is not None:
                print(f"  - {method}: {value:.1f}")
            else:
                print(f"  - {method}: None")

        return results

    except Exception as e:
        print(f"[calculate_all_estimations] 오류: {e}")
        return {}

def get_related_keywords_with_volume(keyword):
    """네이버 검색광고 API를 통해 연관 키워드들과 검색량을 일괄 조회"""
    # 네이버 API용 키워드 전처리 (띄어쓰기 제거)
    api_keyword = keyword.replace(' ', '').strip()
    print("=" * 50)
    print(f"[연관키워드] 함수 호출됨!!! 원본: '{keyword}' → 처리됨: '{api_keyword}'")
    print("=" * 50)
    # 환경 변수 확인
    NAVER_AD_API_KEY = os.getenv('NAVER_AD_API_KEY')
    NAVER_AD_SECRET_KEY = os.getenv('NAVER_AD_SECRET_KEY') 
    NAVER_AD_CUSTOMER_ID = os.getenv('NAVER_AD_CUSTOMER_ID')
    
    print(f"[연관키워드] API 키 확인: API_KEY={NAVER_AD_API_KEY[:10] if NAVER_AD_API_KEY else 'None'}...")
    
    if not all([NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID]):
        print("[연관키워드] 검색광고 API 키가 설정되지 않음")
        return None
    
    try:
        # 네이버 검색광고 API 호출 (키워드 툴)
        timestamp = str(int(time.time() * 1000))
        method = 'GET'
        uri = '/keywordstool'
        
        # 시그니처 생성
        try:
            signature = Signature.generate(timestamp, method, uri, NAVER_AD_SECRET_KEY)
            print(f"[연관키워드] 시그니처 생성 성공")
        except Exception as sig_error:
            print(f"[연관키워드] 시그니처 생성 오류: {sig_error}")
            # fallback 시그니처 생성
            import hashlib
            import hmac
            import base64
            message = f"{timestamp}.{method}.{uri}"
            hash_obj = hmac.new(bytes(NAVER_AD_SECRET_KEY, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)
            signature = base64.b64encode(hash_obj.digest()).decode("utf-8")
        
        url = 'https://api.searchad.naver.com/keywordstool'
        headers = {
            'X-Timestamp': timestamp,
            'X-API-KEY': NAVER_AD_API_KEY,
            'X-Customer': NAVER_AD_CUSTOMER_ID,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }
        
        # 연관 키워드 조회를 위한 파라미터 (showDetail=1로 상세 정보 포함)
        params = {
            'hintKeywords': api_keyword,
            'showDetail': '1'
        }
        
        response = requests.get(url, headers=headers, params=params)
        print(f"[연관키워드] API 응답: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[연관키워드] 응답 데이터 키: {result.keys()}")
            
            if 'keywordList' in result and result['keywordList']:
                keywords_data = result['keywordList']
                print(f"[연관키워드] 총 {len(keywords_data)}개 키워드 발견")
                
                main_keyword_data = None
                related_keywords = []
                
                for i, keyword_data in enumerate(keywords_data):
                    try:
                        print(f"[연관키워드] 처리 중 {i+1}/{len(keywords_data)}")
                        keyword_name = keyword_data.get('relKeyword', '')
                        pc_volume = keyword_data.get('monthlyPcQcCnt', 0) or 0
                        mobile_volume = keyword_data.get('monthlyMobileQcCnt', 0) or 0
                        total_volume = pc_volume + mobile_volume
                        competition = keyword_data.get('compIdx', 'N/A')
                        
                        # 타입 안전성 확보
                        try:
                            pc_volume = int(pc_volume) if pc_volume else 0
                            mobile_volume = int(mobile_volume) if mobile_volume else 0
                            total_volume = pc_volume + mobile_volume
                        except (ValueError, TypeError):
                            pc_volume = 0
                            mobile_volume = 0
                            total_volume = 0
                        
                        keyword_info = {
                            'keyword': str(keyword_name),
                            'monthlySearchVolume': total_volume,
                            'monthlyPcQcCnt': pc_volume,
                            'monthlyMobileQcCnt': mobile_volume,
                            'compIdx': str(competition) if competition else 'N/A'
                        }
                        
                        # 메인 키워드와 정확히 일치하는지 확인 (띄어쓰기 제거된 버전과 비교)
                        if keyword_name.lower() == api_keyword.lower():
                            main_keyword_data = keyword_info
                            print(f"[연관키워드] 메인 키워드 발견: {keyword_name}")
                        else:
                            related_keywords.append(keyword_info)
                            
                    except Exception as keyword_error:
                        print(f"[연관키워드] 키워드 처리 오류 {i+1}: {keyword_error}")
                        continue
                
                print(f"[연관키워드] 연관 키워드 {len(related_keywords)}개 처리 완료")
                
                return {
                    'main_keyword': main_keyword_data,
                    'related_keywords': related_keywords[:20]  # 상위 20개만 반환
                }
            else:
                print("[연관키워드] 키워드 데이터가 없습니다.")
                return None
        else:
            print(f"[연관키워드] API 오류: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"[연관키워드] API 호출 오류: {str(e)}")
        return None

def generate_longtail_keywords(keyword):
    """초보자를 위한 롱테일 키워드 10개 생성"""
    try:
        print(f"[롱테일 키워드] '{keyword}' 기반 생성 시작")
        
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano",  # 정확한 GPT-4.1 Nano 모델명
            messages=[
                {
                    "role": "system",
                    "content": "당신은 SEO 전문가입니다. 블로그 초보자가 상위 노출을 노릴 수 있는 실용적인 롱테일 키워드를 추천해주세요."
                },
                {
                    "role": "user",
                    "content": f"""'{keyword}'이라는 키워드를 기반으로 블로그 초보자가 상위 노출을 노릴 수 있는 롱테일 키워드 10개만 추천해줘.

조건:
1. 문장이 아니라 검색 키워드처럼 짧고 구체적으로
2. 정보형/비교형/후기형/활용형 등 다양한 검색 의도를 고려
3. 제목처럼 문장 형태로 만들지 말고, 실제 사람들이 검색할 법한 3~6단어짜리 키워드만
4. 경쟁이 낮고 초보자도 상위 노출 가능한 키워드
5. 한국어로만 작성

JSON 형식으로 응답해주세요:
{{"longtail_keywords": ["키워드1", "키워드2", "키워드3", ...]}}"""
                }
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        print(f"[롱테일 키워드] API 응답 받음: {response.choices[0].message.content}")
        
        try:
            result = json.loads(response.choices[0].message.content)
            longtail_keywords = result.get('longtail_keywords', [])
            print(f"[롱테일 키워드] JSON 파싱 성공: {longtail_keywords}")
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 기본값
            print(f"[롱테일 키워드] JSON 파싱 실패: {e}")
            print(f"[롱테일 키워드] 원본 응답: {response.choices[0].message.content}")
            longtail_keywords = []
        
        if not longtail_keywords:
            print("[롱테일 키워드] 빈 배열이므로 fallback 사용")
            # 기본 롱테일 키워드 생성
            longtail_keywords = [
                f"{keyword} 추천",
                f"{keyword} 비교",
                f"{keyword} 후기",
                f"{keyword} 장단점",
                f"{keyword} 선택법",
                f"초보자 {keyword}",
                f"{keyword} 가격",
                f"{keyword} 사용법",
                f"{keyword} 종류",
                f"{keyword} 활용팁"
            ]
        
        print(f"[롱테일 키워드] {len(longtail_keywords)}개 생성 완료")
        return longtail_keywords
        
    except Exception as e:
        print(f"[롱테일 키워드] 생성 오류: {e}")
        print(f"[롱테일 키워드] 오류 타입: {type(e)}")
        # 에러 시 기본 키워드 반환
        return [
            f"{keyword} 추천",
            f"{keyword} 비교",
            f"{keyword} 후기",
            f"{keyword} 장단점",
            f"{keyword} 선택법",
            f"초보자 {keyword}",
            f"{keyword} 가격",
            f"{keyword} 사용법",
            f"{keyword} 종류",
            f"{keyword} 활용팁"
        ]

if __name__ == '__main__':
    # Railway 환경변수에서 포트를 가져오되, Railway가 예상하는 포트 사용
    port = int(os.environ.get('PORT', 8080))
    print(f"PORT environment variable value: '{os.environ.get('PORT', 'NOT_SET')}'")
    print(f"All environment variables: {list(os.environ.keys())}")
    print(f"Using port: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
