import pymysql
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# MySQL 연결 설정
db_config = {
    'host': '34.85.84.74',  # MySQL 서버 주소
    'user': 'root',  # MySQL 사용자 이름
    'password': 'woohaha4361!',  # MySQL 비밀번호
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def init_food_data():
    """
    음식 데이터를 초기화하는 함수.
    기본 데이터가 없다면 DB에 값을 추가합니다.
    """
    food_items = ['Pizza', 'Pasta', 'Sushi', 'Ramen', 'Burger', 'Salad']  # 초깃값

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # food_location 테이블에 데이터가 없는 경우에만 데이터 추가
            cursor.execute("SELECT COUNT(*) AS count FROM food_location")
            count = cursor.fetchone()['count']
            if count == 0:
                print("음식 데이터를 초기화하는 중...")
                sql = "INSERT INTO food_location (name) VALUES (%s)"
                for food in food_items:
                    cursor.execute(sql, (food,))
                connection.commit()
                print("음식 데이터 초기화가 완료되었습니다.")
            else:
                print("음식 데이터가 이미 초기화되어 있습니다.")
    except Exception as e:
        print(f"음식 데이터 초기화 오류: {e}")
    finally:
        connection.close()


def init_tourist_data():
    """
    관광지 데이터를 초기화하는 함수.
    """
    tourist_spots = ['Eiffel Tower', 'Great Wall of China', 'Statue of Liberty', 'Taj Mahal', 'Colosseum']

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # tourist_attraction 테이블에 데이터가 없는 경우에만 데이터 추가
            cursor.execute("SELECT COUNT(*) AS count FROM tourist_attraction")
            count = cursor.fetchone()['count']
            if count == 0:
                print("관광지 데이터를 초기화하는 중...")
                sql = "INSERT INTO tourist_attraction (name) VALUES (%s)"
                for spot in tourist_spots:
                    cursor.execute(sql, (spot,))
                connection.commit()
                print("관광지 데이터 초기화가 완료되었습니다.")
            else:
                print("관광지 데이터가 이미 초기화되어 있습니다.")
    except Exception as e:
        print(f"관광지 데이터 초기화 오류: {e}")
    finally:
        connection.close()


@app.before_request
def before_request():
    """
    사용자 요청 이전에 데이터 초기화를 한 번만 수행합니다.
    """
    if not hasattr(app, 'initialized'):  # 초기화 상태 플래그 확인
        print("====== 데이터 초기화를 진행합니다... ======")

        # 관광지 데이터 초기화
        init_tourist_data()

        # 음식 데이터 초기화
        init_food_data()

        app.initialized = True  # 초기화가 완료되었음을 표시


@app.route('/')
def homepage():
    """
    홈페이지를 렌더링합니다.
    """
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    """
    사용자 입력 데이터를 처리하고 DB에 저장합니다.
    """
    lunch = request.form.get('lunch', '0')  # 점심 여부
    dinner = request.form.get('dinner', '0')  # 저녁 여부
    tourist_sites_count = request.form.get('tourist_sites_count', '1')  # 관광지 수

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO user_selection (lunch, dinner, tourist_sites_count)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (lunch, dinner, tourist_sites_count))
            connection.commit()
    except Exception as e:
        print(f"DB 저장 오류: {e}")
    finally:
        connection.close()

    return redirect(url_for('result'))


@app.route('/result')
def result():
    """
    사용자 입력 데이터를 기반으로 랜덤 관광지 및 음식 데이터를 제공합니다.
    """
    try:
        connection = pymysql.connect(**db_config)

        with connection.cursor() as cursor:
            # 최근 사용자 입력 조회
            cursor.execute("SELECT * FROM user_selection ORDER BY id DESC LIMIT 1")
            user_data = cursor.fetchone()

            # 음식 데이터 및 관광지 데이터 가져오기
            lunch = dinner = None
            cursor.execute("SELECT name FROM food_location ORDER BY RAND() LIMIT 1")
            if user_data['lunch'] == '1':  # 점심 여부 확인
                lunch = cursor.fetchone()['name']
            if user_data['dinner'] == '1':  # 저녁 여부 확인
                dinner = cursor.fetchone()['name']

            # 관광지 데이터 가져오기
            attractions = get_tourist_sites(user_data['tourist_sites_count'])  # 랜덤 관광지 호출

        return render_template('result.html', lunch=lunch, dinner=dinner, attractions=attractions)

    finally:
        connection.close()


def get_tourist_sites(limit=1):
    """
    랜덤한 관광지 데이터를 반환하는 함수.
    """
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM tourist_attraction ORDER BY RAND() LIMIT %s", (limit,))
            return [row['name'] for row in cursor.fetchall()]
    except Exception as e:
        print(f"관광지 조회 오류: {e}")
        return []
    finally:
        connection.close()


if __name__ == '__main__':
    app.run(debug=True)
