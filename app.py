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
                    like_conditions.append("category LIKE %s")
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
    import json  # JSON 처리를 위한 모듈 추가
    from urllib.parse import unquote  # URL 디코딩을 위한 함수 추가

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
        # location은 JSON 문자열로 전달되므로 디코딩 후 파싱
        location_str = request.args.get(f'site{i}_location')
        if location_str:
            try:
                location_str = unquote(location_str)  # URL 디코딩
                location = json.loads(location_str)  # JSON 파싱
            except json.JSONDecodeError:
                location = {}  # 파싱 실패 시 빈 객체로 설정
        else:
            location = {}

        site_data[i] = {
            'name': request.args.get(f'site{i}_name'),
            'location': location,  # 파싱된 location 객체 사용
            'image': request.args.get(f'site{i}_image'),
            'address': request.args.get(f'site{i}_address'),
            'id': request.args.get(f'site{i}_id')
        }

    return render_template('process.html', city=city, count=count, site_data=site_data)


@app.route('/live', methods=['POST'])
def live():
    city = request.form.get('city')
    count = request.form.get('count')

    try:
        count = int(count)
        if count < 1 or count > 3:  # count 범위 검사 추가
            return "관광지 개수는 1~3개여야 합니다.", 400
    except ValueError:
        return "잘못된 count 값입니다.", 400

    # 8자리의 고유 usercode 생성 (중복 확인 로직 추가)
    usercode = ''  # usercode 초기화
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
            # 오류 발생 시 루프를 빠져나가거나, 적절한 오류 처리를 할 수 있습니다.
            # 여기서는 간단히 로깅만 하고 다음 시도를 하도록 둡니다.
        finally:
            if 'connection' in locals() and connection.open:  # 연결 상태 확인
                connection.close()

    # process.html 에서 전달받은 관광지 ID 추출 (request.form 사용)
    tourist_sites = []
    missions = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites.append(site_id)

        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                # 1. 관광지의 카테고리 정보 조회
                cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                category_result = cursor.fetchone()

                selected_category_for_mission = None
                if category_result and category_result['category']:
                    # 2. 쉼표로 구분된 카테고리 문자열을 리스트로 분리
                    categories_list = [cat.strip() for cat in category_result['category'].split(',')]
                    if categories_list:
                        # 3. 분리된 카테고리 중 하나를 랜덤하게 선택
                        selected_category_for_mission = random.choice(categories_list)

                mission_id = None
                if selected_category_for_mission:
                    # 4. 선택된 단일 카테고리로 미션 검색
                    cursor.execute("SELECT id FROM mission WHERE category = %s ORDER BY RAND() LIMIT 1",
                                   (selected_category_for_mission,))
                    mission_id_result = cursor.fetchone()
                    if mission_id_result:
                        mission_id = mission_id_result['id']

                missions.append(mission_id)

        except Exception as e:
            print(f"미션 ID 조회 오류 (site_id: {site_id}): {e}")
            missions.append(None)  # 오류 발생 시 해당 미션은 None으로 추가
        finally:
            if 'connection' in locals() and connection.open:  # 연결 상태 확인
                connection.close()

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리와 매개변수를 동적으로 생성
            columns_list = [f"tourist_site_{i}" for i in range(1, count + 1)] + \
                           [f"mission_{i}" for i in range(1, count + 1)]
            columns = ", ".join(columns_list)

            # count에 맞춰 placeholders 생성
            placeholders_list = ["%s"] * (count + count)  # 관광지 ID 개수 + 미션 ID 개수
            placeholders = ", ".join(placeholders_list)

            sql = f"""
                   INSERT INTO user_travel_data (usercode, {columns}) 
                   VALUES (%s, {placeholders})
               """

            # params 리스트 생성 시, tourist_sites와 missions 리스트의 길이를 count에 맞게 조정
            # 만약 count보다 적은 관광지나 미션이 선택되었을 경우를 대비하여 None으로 채울 수 있습니다.
            # 현재 로직에서는 tourist_sites는 count만큼 채워지고, missions도 count만큼 채워집니다 (성공 또는 None).
            params = [usercode] + tourist_sites[:count] + missions[:count]

            cursor.execute(sql, params)
            connection.commit()
    except Exception as e:
        print(f"데이터베이스 삽입 오류: {e}")
        if 'connection' in locals() and connection.open:  # 연결 상태 확인
            connection.rollback()
        return "오류 발생!", 500
    finally:
        if 'connection' in locals() and connection.open:  # 연결 상태 확인
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
# app.py (새로운 라우트를 추가하세요)
@app.route('/mission.html')
def mission_page():
    return render_template('mission.html')

# 기존 /get_mission_details/<usercode> 라우트도 그대로 유지되어야 합니다.
@app.route('/get_mission_details/<usercode>')
def get_mission_details(usercode):
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # Get mission IDs and their confirmed status from user_travel_data
            # 모든 mission_X 와 mission_X_confirmed 필드를 가져오도록 SQL 수정
            sql_user_missions = """
                SELECT mission_1, mission_1_confirmed, 
                       mission_2, mission_2_confirmed, 
                       mission_3, mission_3_confirmed 
                FROM user_travel_data 
                WHERE usercode = %s
            """
            cursor.execute(sql_user_missions, (usercode,))
            user_missions_status = cursor.fetchone()

            missions_data = []
            if user_missions_status:
                for i in range(1, 4):  # Assuming up to mission_3
                    mission_id = user_missions_status.get(f'mission_{i}')
                    mission_confirmed = user_missions_status.get(f'mission_{i}_confirmed')

                    # mission_confirmed가 None일 경우 (DB에 아직 값이 없을 수 있음) False로 간주
                    if mission_confirmed is None:
                        mission_confirmed = False
                    else:
                        mission_confirmed = bool(mission_confirmed)  # DB에서 TINYINT(1) 등으로 오면 0 또는 1이므로 boolean으로 변환

                    if mission_id:
                        # Get mission details from the mission table
                        sql_mission_details = "SELECT title, content FROM mission WHERE id = %s"
                        cursor.execute(sql_mission_details, (mission_id,))
                        mission_detail = cursor.fetchone()
                        if mission_detail:
                            missions_data.append({
                                'id': mission_id,
                                'title': mission_detail['title'],
                                'content': mission_detail['content'],
                                'confirmed': mission_confirmed,  # 확정 상태 추가
                                'mission_seq': i  # 미션 순번 추가 (1, 2, or 3)
                            })
        return jsonify({"success": True, "missions": missions_data})
    except Exception as e:
        print(f"미션 상세 정보 조회 오류: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()


@app.route('/update_mission_status', methods=['POST'])
def update_mission_status():
    data = request.get_json()
    usercode = data.get('usercode')
    mission_seq = data.get('mission_seq')  # 1, 2, or 3
    is_confirmed = data.get('confirmed')  # true or false

    if not all([usercode, mission_seq is not None, is_confirmed is not None]):
        return jsonify({"success": False, "error": "필수 파라미터가 누락되었습니다."}), 400

    if not isinstance(mission_seq, int) or not (1 <= mission_seq <= 3):
        return jsonify({"success": False, "error": "잘못된 mission_seq 값입니다."}), 400

    # DB의 TINYINT(1) 저장을 위해 boolean을 0 또는 1로 변환
    confirmed_value = 1 if is_confirmed else 0

    # 동적으로 컬럼 이름 생성
    mission_confirmed_column = f'mission_{mission_seq}_confirmed'

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL UPDATE 문 구성
            # 주의: 컬럼 이름을 직접 포맷팅할 때는 SQL 인젝션에 매우 주의해야 합니다.
            # 여기서는 mission_seq가 1, 2, 3 중 하나임을 검증했으므로 안전하다고 가정합니다.
            sql = f"UPDATE user_travel_data SET {mission_confirmed_column} = %s WHERE usercode = %s"

            cursor.execute(sql, (confirmed_value, usercode))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({"success": True, "message": "미션 상태가 업데이트되었습니다."})
            else:
                return jsonify({"success": False, "error": "해당 usercode를 찾을 수 없거나 업데이트할 내용이 없습니다."}), 404

    except Exception as e:
        print(f"미션 상태 업데이트 오류: {e}")
        if 'connection' in locals() and connection.open:
            connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'connection' in locals() and connection.open:
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


