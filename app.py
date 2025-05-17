from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pymysql
import atexit
import sys

# tourist_attraction.py에서 함수 가져오기
from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db

app = Flask(__name__)

# MySQL DB 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소
    'user': 'outer',  # MySQL 사용자 이름
    'password': 'outeropensql',  # MySQL 비밀번호
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    if not city or city == "none":
        return "도시를 선택하세요!", 400
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    city = request.args.get('city')
    count = request.args.get('count')

    return render_template('result.html', city=city, count=count)


@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT name FROM category"
            cursor.execute(sql)
            categories = [row['name'] for row in cursor.fetchall()]

        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()

def insert_missions():
    """미션 데이터를 데이터베이스에 삽입합니다."""
    try:
        # MySQL 연결
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO mission (title, content, category) VALUES
            ('인증샷 찍기', '이 공원에서 가장 멋진 인증샷을 찍어보세요!', '공원'),
            ('좋은 공기를 느껴보세요!', '공원 2km 걷기!', '공원'),
            ('좋은 공기를 느껴보세요!', '공원 1.5km 걷기!', '공원'),
            ('나무 이름 맞추기', '공원 내 특정 나무의 이름을 맞추고 설명판을 찍어오세요.', '공원'),
            ('공원에서 휴식하기', '돗자리를 펴고 30분 이상 휴식을 취하며 공원의 분위기를 느껴보세요.', '공원'),
            ('공원 동물 관찰하기', '공원에서 볼 수 있는 동물(새, 곤충 등)을 2종류 이상 관찰하고 기록해보세요.', '공원'),
            ('공원 역사 알아보기', '공원의 역사 또는 유래에 대한 정보를 찾아보고, 가장 흥미로운 사실을 적어보세요.', '공원'),
            ('공원 쓰레기 줍기', '공원을 깨끗하게 만들기 위해 쓰레기를 7개 이상 주워주세요.', '공원'),
            ('공원 쓰레기 줍기', '공원을 깨끗하게 만들기 위해 쓰레기를 10개 이상 주워주세요.', '공원'),
            ('공원 시 짓기', '공원에서 영감을 받아 짧은 시를 지어보세요.', '공원'),
            ('공원 음악 감상', '이어폰 없이 공원의 자연의 소리를 들으며 음악을 감상해보세요.', '공원'),
            ('공원 요가/스트레칭', '공원에서 간단한 요가나 스트레칭을 하며 몸을 풀어보세요.', '공원'),
            ('공원 독서', '공원에서 책을 읽으며 여유로운 시간을 보내세요.', '공원'),
            ('공원 벤치에서 사색', '공원 벤치에 앉아 10분 동안 조용히 사색에 잠겨보세요.', '공원'),
            ('공원 벤치에서 사색', '공원 벤치에 앉아 15분 동안 조용히 사색에 잠겨보세요.', '공원'),
            ('박물관 인증샷', '박물관에서 가장 마음에 드는 전시품 앞에서 인증샷을 찍어보세요.', '박물관'),
            ('전시품 설명 읽기', '전시품 3개의 설명을 자세히 읽고, 가장 흥미로웠던 내용을 적어보세요.', '박물관'),
            ('전시품 설명 읽기', '전시품 2개의 설명을 자세히 읽고, 가장 흥미로웠던 내용을 적어보세요.', '박물관'),
            ('전시품 설명 읽기', '전시품 1개의 설명을 자세히 읽고, 가장 흥미로웠던 내용을 적어보세요.', '박물관'),
            ('나만의 전시 기획', '내가 박물관 큐레이터라면 어떤 전시를 기획하고 싶은지 적어보세요.', '박물관'),
            ('박물관 후기 작성', '박물관 방문 후기를 온라인에 작성하고, 링크를 공유해주세요.', '박물관'),
            ('정상 인증샷', '산 정상에서 인증샷을 찍어보세요!', '산'),
            ('등산로 따라 걷기', '정해진 등산로를 따라 2시간 이상 걸어보세요.', '산'),
            ('등산로 따라 걷기', '정해진 등산로를 따라 1시간 30분 이상 걸어보세요.', '산'),
            ('야생화 사진 찍기', '산에서 자라는 야생화 3종류 이상을 찾아 사진을 찍어보세요.', '산'),
            ('야생화 사진 찍기', '산에서 자라는 야생화 2종류 이상을 찾아 사진을 찍어보세요.', '산'),
            ('정상에서 간식 먹기', '정상에서 준비해 온 간식을 먹으며 경치를 감상하세요.', '산'),
            ('등산 중 만난 사람과 인사', '등산 중 만난 사람들에게 밝게 인사해보세요.', '산'),
            ('하산길에 쓰레기 줍기', '하산하면서 보이는 쓰레기를 7개 이상 주워주세요.', '산'),
            ('하산길에 쓰레기 줍기', '하산하면서 보이는 쓰레기를 10개 이상 주워주세요.', '산'),
            ('정상 표지판 사진 찍기', '정상에 있는 표지판과 함께 사진을 찍어 추억을 남기세요.', '산'),
            ('등산 코스 기록', '등산 코스를 기록하고, 소요 시간과 난이도를 평가해보세요.', '산'),
            ('산에서 명상하기', '조용한 곳에서 잠시 눈을 감고 명상하며 자연의 소리에 귀 기울여보세요.', '산'),
            ('산 이름 유래 알아보기', '산 이름의 유래를 알아보고, 관련된 이야기를 적어보세요.', '산'),
            ('등산 장비 점검', '등산 장비를 점검하고, 안전하게 등산을 마쳤는지 확인해보세요.', '산'),
            ('산행 후기 작성', '등산 후기를 온라인에 작성하고, 다른 사람들에게 추천해주세요.', '산')
            """
            cursor.execute(sql)
            connection.commit()
        print("미션 데이터가 성공적으로 삽입되었습니다.")
    except Exception as e:
        print(f"미션 데이터 삽입 오류: {e}")
    finally:
        if 'connection' in locals():
            connection.close()



@app.route('/insert_initial_missions')  # 이 라우트를 통해 미션 데이터를 삽입할 수 있습니다.
def insert_initial_missions_route():
    insert_missions()
    return "초기 미션 데이터 삽입 완료", 200





@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리 수정: mapx, mapy 컬럼 추가
            sql = "SELECT id, name, address, mapx, mapy, image FROM tourist_attraction WHERE address LIKE %s"
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category in category_list:
                    like_conditions.append("name LIKE %s")
                    params.append(f"%{category}%")

                sql += " AND (" + " OR ".join(like_conditions) + ")"

            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # 각 관광지 정보에 mapx, mapy 정보를 location 객체에 추가
            for result in results:
                result['location'] = {'mapx': result['mapx'], 'mapy': result['mapy']}

        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()



@app.route('/process')
def process():
    return render_template('process.html',
                           city=request.args.get('city'),
                           count=request.args.get('count'))


@app.route('/live')
def live():
    city = request.args.get('city')
    count = request.args.get('count')
    return render_template('live.html', city=city, count=count)

def update_tourist_attractions():
    """
    tourist_attraction.py에 정의된 함수들을 사용해서 관광 데이터를 갱신합니다.
    """
    print("관광지 데이터 갱신 작업 시작...")

    # API를 통해 관광지 데이터 가져오기
    from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db
    tourist_sites = get_tourist_sites()

    # 가져온 데이터를 데이터베이스에 저장
    save_tourist_sites_to_db(tourist_sites)

    print("관광지 데이터 갱신 작업 완료!")


# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.start()

# 스케줄링 작업 등록
scheduler.add_job(
    func=update_tourist_attractions,  # 실행할 작업 함수
    trigger=IntervalTrigger(days=1),  # 1분마다 실행

    id="update_tourist_attractions_job",  # 고유 작업 ID
    name="관광지 데이터 갱신 작업",  # 작업 이름
    replace_existing=True  # 동일 ID가 있을 경우 기존 작업 대체
)

# 애플리케이션 종료 시 스케줄러도 종료
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    print("스케줄러가 실행 중입니다...")
    app.run(host='0.0.0.0', port=5000, debug=True)


