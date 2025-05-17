from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pymysql
import atexit
import sys
import random
import string

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
            sql = "SELECT id, name, address, mapx, mapy, image, category FROM tourist_attraction WHERE address LIKE %s"  # category 컬럼 추가
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
    city = request.args.get('city')
    count = request.args.get('count')
    # count 변수를 정수형으로 변환
    try:
        count = int(count)  # count를 int형으로 변환
    except ValueError:
        return "잘못된 count 값입니다.", 400

    # site 정보를 딕셔너리로 변환
    site_data = {}
    for i in range(1, count + 1):
        site_data[i] = {
            'name': request.args.get(f'site{i}_name'),
            'location': request.args.get(f'site{i}_location'),
            'image': request.args.get(f'site{i}_image'),
            'address': request.args.get(f'site{i}_address'),
            'id': request.args.get(f'site{i}_id')
        }

    return render_template('process.html', city=city, count=count, site_data=site_data)



@app.route('/live', methods=['POST'])
def live():
    city = request.form.get('city')
    count = request.form.get('count')  # count 값을 request.form 에서 가져옴

    try:
        count = int(count)
    except ValueError:
        return "잘못된 count 값입니다.", 400

    # 8자리의 고유 usercode 생성 (중복 확인 로직 추가)
    while True:
        usercode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    break  # 중복되지 않는 usercode 생성 완료
        except Exception as e:
            print(f"usercode 중복 확인 오류: {e}")
        finally:
            if 'connection' in locals():
                connection.close()

    # process.html 에서 전달받은 관광지 ID 추출 (request.form 사용)
    tourist_sites = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites.append(site_id)

    # mission 테이블에서 category를 이용하여 mission id 가져오기 (랜덤으로 1개 선택, None 처리 추가)
    missions = []
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            for i in range(1, count + 1):
                site_id = request.form.get(f'site{i}_id')
                cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                category_result = cursor.fetchone()
                category = category_result['category'] if category_result else None  # category가 None일 경우 처리

                if category:  # category가 존재하는 경우에만 쿼리 실행
                    cursor.execute("SELECT id FROM mission WHERE category = %s ORDER BY RAND() LIMIT 1", (category,))
                    mission_id_result = cursor.fetchone()
                    mission_id = mission_id_result['id'] if mission_id_result else None  # mission_id가 None일 경우 처리
                    missions.append(mission_id)
                else:
                    missions.append(None)  # category가 없을 경우 None을 추가


    except Exception as e:
        print(f"미션 ID 조회 오류: {e}")
        return "오류 발생!", 500
    finally:
        if 'connection' in locals():
            connection.close()

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리 수정: count에 따라 컬럼 수 동적으로 조정
            sql = f"""
                INSERT INTO user_travel_data (usercode, tourist_site_1, tourist_site_2, tourist_site_3, mission_1, mission_2, mission_3) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            # SQL 쿼리와 값을 count에 맞춰서 동적으로 생성해야 합니다.
            # 현재는 count가 3 이상일 때 오류가 발생합니다.
            # count에 따라 컬럼과 값을 동적으로 생성하는 로직이 필요합니다.

            cursor.execute(sql, (usercode, *tourist_sites, *missions))  # * 연산자를 사용해서 리스트의 요소를 개별 매개변수로 전달
            connection.commit()
    except Exception as e:
        print(f"데이터베이스 삽입 오류: {e}")
        connection.rollback()
        return "오류 발생!", 500
    finally:
        if 'connection' in locals():
            connection.close()

    return render_template('live.html', city=city, count=count, usercode=usercode)



def get_mission_id_by_category(category):
    """tourist_attraction 테이블의 카테고리와 같은 category를 가진 mission의 id를 반환합니다.
        (구현 필요:  tourist_attraction 테이블과 mission 테이블의 관계에 따라 수정해야 합니다.)"""
    # 이 부분은 tourist_attraction과 mission 테이블의 관계와 데이터 구조에 따라 구현해야 합니다.
    # 예시:  두 테이블의 category 컬럼을 비교하여 mission id를 찾는 로직 추가
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT id FROM mission WHERE category = %s LIMIT 1"  # 중복 방지를 위해 LIMIT 1 추가
            cursor.execute(sql, (category,))
            result = cursor.fetchone()
            return result['id'] if result else None
    except Exception as e:
        print(f"미션 ID 조회 오류: {e}")
        return None
    finally:
        if 'connection' in locals():
            connection.close()

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


