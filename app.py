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
    missions = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites.append(site_id)

        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                category_result = cursor.fetchone()
                category = category_result['category'] if category_result else None

                if category:
                    cursor.execute("SELECT id FROM mission WHERE category = %s ORDER BY RAND() LIMIT 1", (category,))
                    mission_id_result = cursor.fetchone()
                    mission_id = mission_id_result['id'] if mission_id_result else None
                    missions.append(mission_id)
                else:
                    missions.append(None)
        except Exception as e:
            print(f"미션 ID 조회 오류: {e}")
            return "오류 발생!", 500
        finally:
            if 'connection' in locals():
                connection.close()

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리와 매개변수를 동적으로 생성
            columns = ", ".join(
                [f"tourist_site_{i}" for i in range(1, count + 1)] + [f"mission_{i}" for i in range(1, count + 1)])
            placeholders = ", ".join(["%s"] * (2 * count))  # 매개변수 자리 표시자 생성

            sql = f"""
                   INSERT INTO user_travel_data (usercode, {columns}) 
                   VALUES (%s, {placeholders})
               """

            params = [usercode] + tourist_sites + missions  # 매개변수 리스트 생성

            cursor.execute(sql, params)
            connection.commit()
    except Exception as e:
        print(f"데이터베이스 삽입 오류: {e}")
        connection.rollback()
        return "오류 발생!", 500
    finally:
        if 'connection' in locals():
            connection.close()

    return render_template('live.html', city=city, count=count, usercode=usercode)

@app.route('/review/<usercode>')
def review_page(usercode):
    """
    사용자 코드를 받아 해당 여행에 대한 관광지 목록을 조회하고 후기 페이지를 렌더링합니다.
    """
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # user_travel_data 테이블에서 해당 usercode의 데이터 조회
            cursor.execute(f"SELECT * FROM user_travel_data WHERE usercode = %s", (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return "여행 데이터가 존재하지 않습니다.", 404

            selected_site_ids = []
            # user_travel_data 테이블의 tourist_site_1, tourist_site_2, tourist_site_3 컬럼에서 ID 추출
            for i in range(1, 4): # 최대 3개 관광지 가정
                site_key = f'tourist_site_{i}'
                if site_key in user_data and user_data[site_key]:
                    selected_site_ids.append(user_data[site_key])

        sites_to_review = []
        for site_id in selected_site_ids:
            site_details = get_site_details_by_id(site_id)
            if site_details:
                sites_to_review.append(site_details)

        return render_template('review.html', usercode=usercode, sites_to_review=sites_to_review)

    except Exception as e:
        print(f"Error in review_page for usercode {usercode}: {e}")
        return "후기 페이지를 불러오는 중 오류가 발생했습니다.", 500
    finally:
        if conn:
            conn.close()

@app.route('/submit_review', methods=['POST'])
def submit_review():
    """
    후기 페이지에서 제출된 데이터를 받아 데이터베이스의 `review` 테이블에 저장
    별점 부여(1-5) -> raitng
    """
    usercode = request.form.get('usercode')

    conn = None
    try:
        conn = connection = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # 폼 데이터를 순회하며 각 관광지에 대한 후기 추출 및 저장
            for key, value in request.form.items():
                if key.startswith('review_text_'):  # 후기 텍스트 필드 식별
                    site_id = key.replace('review_text_', '')
                    review_content = value.strip()  # 공백 제거

                    # 변경: 별점 입력 필드에서 값 가져오기
                    rating_str = request.form.get(f'rating_{site_id}')  # 'rating_' 접두사로 변경
                    rating_value = None  # 기본값은 None (NULL 허용 시)

                    if rating_str:
                        try:
                            rating_value = int(rating_str)  # 문자열을 정수로 변환
                            # 별점 범위 유효성 검사 (1~5점)
                            if not (1 <= rating_value <= 5):
                                rating_value = None  # 유효하지 않은 값은 None으로 처리하거나 기본값 설정
                        except ValueError:
                            rating_value = None  # 정수로 변환 불가능한 경우 None

                    # tourist_attraction_id와 content (또는 rating) 값이 하나라도 있다면 저장
                    # rating_value가 0인 경우도 저장되도록 'is not None'을 사용
                    # (여기서는 1~5점이므로 0은 해당 없지만, Null 허용을 위해)
                    if site_id and (review_content or rating_value is not None):
                        sql = """
                           INSERT INTO review (tourist_attraction_id, content, rating)
                           VALUES (%s, %s, %s)
                           """
                        cursor.execute(sql, (site_id, review_content, rating_value))
            conn.commit()  # 모든 후기 저장 후 한 번만 커밋

        return redirect(url_for('review_success'))

    except Exception as e:
        print(f"Error submitting review for usercode {usercode}: {e}", file=sys.stderr)
        if conn:
            conn.rollback()  # 오류 발생 시 롤백
        return "후기를 제출하는 중 오류가 발생했습니다.", 500
    finally:
        if conn:
            conn.close()

@app.route('/review_success')
def review_success():
    """후기 제출 성공 페이지."""
    return render_template('review_success.html')

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

def get_site_details_by_id(site_id):
    """tourist_attraction 테이블에서 site_id에 해당하는 관광지 상세 정보를 조회합니다."""
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            sql = "SELECT id, name, image, address FROM tourist_attraction WHERE id = %s"
            cursor.execute(sql, (site_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching site details for {site_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


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


