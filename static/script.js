async function searchKeyword() {
    const keywordInput = document.getElementById('keyword');
    const keyword = keywordInput.value.trim();
    
    if (!keyword) {
        alert('키워드를 입력해주세요');
        return;
    }

    // 로딩 표시
    const loading = document.getElementById('loading');
    const resultCard = document.getElementById('resultCard');
    
    loading.style.display = 'block';
    resultCard.style.display = 'none';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ keyword }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        console.log('받은 전체 데이터:', data);

        // 월간 추정치 디버깅 출력
        if (data.monthlyEstimates) {
            console.log('월간 추정치 결과:', data.monthlyEstimates);
            console.log('최종 월간 추정치:', data.finalMonthlyEstimate);
        }

        // 검색 트렌드 차트 생성
        if (data.searchTrend && data.searchTrend.graphData) {
            createSearchTrendChart(data.searchTrend.graphData);
        }

        // 통계 데이터 표시
        updateStatistics(data);

        // 분석 결과 표시
        if (data.analysis) {
            console.log('받은 분석 데이터:', data.analysis);
            displayAnalysis(data.analysis);
        }

        // 블로그 데이터 표시
        updatePosts('blog', data.blog.recentPosts, data.blog.total);

        // 카페 데이터 표시
        updatePosts('cafe', data.cafe.recentPosts, data.cafe.total);

        // 월간 발행량 추정치 표시 (기존 누적량 대신)
        const finalEstimate = data.finalMonthlyEstimate || 0;
        const blogEstimate = Math.round(finalEstimate * 0.6); // 블로그 60%
        const cafeEstimate = Math.round(finalEstimate * 0.4); // 카페 40%
        
        document.getElementById('blogTotal').textContent = blogEstimate.toLocaleString();
        document.getElementById('cafeTotal').textContent = cafeEstimate.toLocaleString();
        document.getElementById('totalContent').textContent = Math.round(finalEstimate).toLocaleString();

        // 연관검색어 표시 (새로 추가)
        if (data.relatedKeywords) {
            displayRelatedKeywords(data.relatedKeywords, data);
        }

        // 롱테일 키워드 표시 (초보자용)
        if (data.longtailKeywords) {
            displayLongtailKeywords(data.longtailKeywords);
        }

        // 디버깅용 콘솔 출력
        console.log(`월간 발행량 추정치 - 블로그: ${blogEstimate}, 카페: ${cafeEstimate}, 전체: ${Math.round(finalEstimate)}`);
        console.log('연관검색어:', data.relatedKeywords);
        console.log('롱테일 키워드:', data.longtailKeywords);

        loading.style.display = 'none';
        resultCard.style.display = 'block';
        
    } catch (error) {
        console.error('API 호출 에러:', error);
        loading.style.display = 'none';
        alert(`검색 중 오류가 발생했습니다: ${error.message}`);
    }
}

function updateStatistics(data) {
    // API에서 실제 검색량을 가져온 경우에만 표시
    if (data.searchVolume && 
        data.searchVolume.monthlyPcQcCnt && 
        data.searchVolume.monthlyMobileQcCnt &&
        typeof data.searchVolume.monthlyPcQcCnt === 'number' &&
        typeof data.searchVolume.monthlyMobileQcCnt === 'number') {
        
        // 실제 검색량이 있는 경우
        const pcVolume = data.searchVolume.monthlyPcQcCnt;
        const mobileVolume = data.searchVolume.monthlyMobileQcCnt;
        const totalVolume = pcVolume + mobileVolume;
        
        document.getElementById('latestPcVolume').textContent = pcVolume.toLocaleString();
        document.getElementById('latestMobileVolume').textContent = mobileVolume.toLocaleString();
        document.getElementById('latestTotalVolume').textContent = totalVolume.toLocaleString();
        
        console.log('✅ 실제 검색량 데이터를 사용합니다:', {pc: pcVolume, mobile: mobileVolume, total: totalVolume});
    } else {
        // 실제 검색량이 없으면 아예 표시하지 않음
        document.getElementById('latestPcVolume').textContent = '데이터 없음';
        document.getElementById('latestMobileVolume').textContent = '데이터 없음';
        document.getElementById('latestTotalVolume').textContent = '데이터 없음';
        
        console.log('⚠️ 실제 검색량 데이터가 없습니다. API 설정을 확인하세요.');
    }
}

function displayAnalysis(analysis) {
    console.log('분석 결과 표시:', analysis);
    
    // 한글 키 이름으로 접근
    const saturationRate = analysis['포화지수'] || analysis.saturationRate || '-';
    const opportunityScore = analysis['기회점수'] || analysis.opportunityScore || '-';
    const grade = analysis['등급'] || analysis.grade || '-';
    
    document.getElementById('saturationRate').textContent = saturationRate;
    document.getElementById('opportunityScore').textContent = opportunityScore;
    document.getElementById('grade').textContent = grade;
    
    // 등급에 따른 색상 적용
    const gradeElement = document.getElementById('grade');
    if (grade && grade !== '-') {
        // 기존 클래스 제거
        gradeElement.classList.remove('grade-a', 'grade-b', 'grade-c', 'grade-d', 'grade-f');
        
        // 등급에 따른 색상 클래스 추가
        const gradeClass = grade.toLowerCase().replace('+', '');
        gradeElement.classList.add(`grade-${gradeClass}`);
    }
}

function createSearchTrendChart(data) {
    // Plotly가 로드될 때까지 기다림
    if (typeof Plotly === 'undefined') {
        setTimeout(() => createSearchTrendChart(data), 100);
        return;
    }

    const dates = data.dates || [];
    const ratios = data.ratios || [];

    if (dates.length === 0 || ratios.length === 0) {
        document.getElementById('searchTrendChart').innerHTML = '<p class="no-results">차트 데이터가 없습니다.</p>';
        return;
    }

    const trace = {
        x: dates,
        y: ratios,
        name: '검색 트렌드',
        type: 'scatter',
        mode: 'lines+markers',
        line: { 
            color: '#1a73e8',
            width: 3
        },
        marker: {
            size: 8,
            color: '#1a73e8'
        },
        fill: 'tonexty',
        fillcolor: 'rgba(26, 115, 232, 0.1)'
    };

    const layout = {
        showlegend: false,
        xaxis: {
            title: '',
            tickformat: '%Y-%m',
            gridcolor: '#f1f3f4',
            showgrid: true
        },
        yaxis: {
            title: '',
            gridcolor: '#f1f3f4',
            showgrid: true
        },
        height: 300,
        margin: {
            l: 40,
            r: 40,
            t: 20,
            b: 40
        },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot('searchTrendChart', [trace], layout, config);
}

function updatePosts(type, posts, total) {
    const postsContainer = document.getElementById(`${type}Posts`);
    const countElement = document.getElementById(`${type}Count`);
    
    // 총 개수 표시 (상단 헤더) - 누적 총량으로 표시
    if (countElement) {
        countElement.textContent = `${total.toLocaleString()}건 (누적)`;
    }
    
    if (postsContainer) {
        postsContainer.innerHTML = '';
        
        if (posts && posts.length > 0) {
            posts.forEach(post => {
                const postElement = document.createElement('div');
                postElement.className = 'post-item';
                
                // HTML 태그 제거
                const cleanTitle = post.title.replace(/<[^>]*>/g, '');
                const cleanDescription = post.description.replace(/<[^>]*>/g, '');
                
                // 설명 글자 수 제한
                const truncatedDescription = cleanDescription.length > 80 
                    ? cleanDescription.substring(0, 80) + '...' 
                    : cleanDescription;
                
                postElement.innerHTML = `
                    <div class="post-title">
                        <a href="${post.link}" target="_blank" rel="noopener noreferrer">${cleanTitle}</a>
                    </div>
                    <div class="post-description">${truncatedDescription}</div>
                    <div class="post-date">${post.date}</div>
                `;
                postsContainer.appendChild(postElement);
            });
        } else {
            postsContainer.innerHTML = '<p class="no-results">검색 결과가 없습니다.</p>';
        }
    }
}

// Enter 키 이벤트 처리 (한 번만)
document.addEventListener('DOMContentLoaded', function() {
    const keywordInput = document.getElementById('keyword');
    if (keywordInput) {
        keywordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchKeyword();
            }
        });
        
        // 포커스 설정
        keywordInput.focus();
    }
});

// 페이지 로드 시 Plotly 확인 (한 번만)
window.addEventListener('load', function() {
    if (typeof Plotly !== 'undefined') {
        console.log('✅ Plotly 로드 완료');
    } else {
        console.warn('❌ Plotly 로드되지 않았습니다. 차트가 표시되지 않을 수 있습니다.');
    }
});

// 연관검색어 표시 함수 (테이블 형태로 수정)
function displayRelatedKeywords(keywords, mainData) {
    const tbody = document.getElementById('relatedKeywords');
    
    if (!tbody) {
        console.warn('연관검색어 테이블을 찾을 수 없습니다.');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (keywords && keywords.length > 0) {
        // 메인 키워드의 실제 검색량 가져오기
        let mainTotalVolume = 0;
        if (mainData.searchVolume) {
            mainTotalVolume = (mainData.searchVolume.monthlyPcQcCnt || 0) + (mainData.searchVolume.monthlyMobileQcCnt || 0);
        }
        
        keywords.forEach((keywordData, index) => {
            const row = document.createElement('tr');
            
            // 키워드 데이터 추출
            const keywordName = keywordData.keyword || keywordData;
            let searchVolume = keywordData.monthlySearchVolume;
            let monthlyContent = '-';
            const competition = keywordData.compIdx || '-';
            
            // 검색량이 없으면 표시하지 않음 (하드코딩 제거)
            if (!searchVolume || searchVolume === null) {
                searchVolume = null; // 데이터 없음으로 표시
            }
            
            // 월간 발행량은 실제 데이터가 있을 때만 표시
            if (searchVolume && searchVolume > 0) {
                // 실제 검색량 기반으로만 추정
                const contentRatio = 0.3; // 고정 비율 사용
                monthlyContent = Math.round(searchVolume * contentRatio);
            } else {
                monthlyContent = null; // 데이터 없음
            }
            
            // 경쟁도 색상 클래스
            let competitionClass = '';
            if (competition === '높음') competitionClass = 'competition-high';
            else if (competition === '중간') competitionClass = 'competition-medium';
            else if (competition === '낮음') competitionClass = 'competition-low';
            
            row.innerHTML = `
                <td class="keyword-name">${keywordName}</td>
                <td class="search-volume">${searchVolume && searchVolume > 0 ? searchVolume.toLocaleString() : '-'}</td>
                <td>${monthlyContent && monthlyContent > 0 ? monthlyContent.toLocaleString() : '-'}</td>
                <td class="${competitionClass}">${competition}</td>
            `;
            
            // 클릭 시 해당 키워드로 새 검색
            row.addEventListener('click', function() {
                document.getElementById('keyword').value = keywordName;
                searchKeyword();
            });
            
            tbody.appendChild(row);
        });
        
        console.log(`✅ 연관검색어 ${keywords.length}개 테이블 표시 완료`);
        console.log(`메인 키워드 검색량: ${mainTotalVolume.toLocaleString()}`);
    } else {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="no-results">연관검색어가 없습니다.</td>';
        tbody.appendChild(row);
    }
}

// 글감 생성 페이지로 이동 함수
function goToTopicGenerator() {
    const keyword = document.getElementById('keyword').value.trim();
    if (keyword) {
        // 키워드를 URL 파라미터로 전달하며 글감 생성 페이지로 이동
        window.location.href = `/topic-generator?keyword=${encodeURIComponent(keyword)}`;
    } else {
        // 키워드가 없으면 그냥 글감 생성 페이지로 이동
        window.location.href = '/topic-generator';
    }
}

// 내보내기 알림 함수
function showExportNotice() {
    alert('내보내기 기능은 "전체글 완성" 페이지에서 사용할 수 있습니다.\n\n워크플로우:\n1. 키워드 분석 완료\n2. 글감 생성으로 이동\n3. 전체글 완성으로 이동\n4. 글 생성 후 내보내기 버튼 클릭');
}

// 롱테일 키워드 표시 함수
function displayLongtailKeywords(keywords) {
    const container = document.getElementById('longtailKeywords');
    
    if (!container) {
        console.warn('롱테일 키워드 컨테이너를 찾을 수 없습니다.');
        return;
    }
    
    container.innerHTML = '';
    
    if (keywords && keywords.length > 0) {
        keywords.forEach((keyword) => {
            const keywordTag = document.createElement('div');
            keywordTag.className = 'longtail-keyword-tag';
            keywordTag.textContent = keyword;
            
            // 클릭 시 해당 키워드로 새 검색
            keywordTag.addEventListener('click', function() {
                document.getElementById('keyword').value = keyword;
                searchKeyword();
            });
            
            container.appendChild(keywordTag);
        });
        
        console.log(`✅ 롱테일 키워드 ${keywords.length}개 표시 완료`);
    } else {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = '롱테일 키워드를 생성할 수 없습니다.';
        container.appendChild(noResults);
    }
}