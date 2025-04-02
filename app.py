import pymysql
from flask import Flask, render_template, request, redirect, url_for
import random

app = Flask(__name__)

# MySQL 연결 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소 (변경된 IP)
    'user': 'outer',  # MySQL 사용자 이름 (변경된 사용자)
    'password': 'outeropensql',  # MySQL 비밀번호 (변경된 비밀번호)
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',  # 문자셋 설정
    'cursorclass': pymysql.cursors.DictCursor  # DictCursor로 결과 반환
}



def init_food_data():
    """
    음식 데이터를 초기화하는 함수.
    기본 데이터가 없다면 DB에 값을 추가합니다.
    """
    food_items = ['', '', '', '', '', '']  # 초깃값

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
    tourist_spots = ['', '', '', '', '']

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
    사용자 입력 데이터를 기반으로 점심, 저녁, 관광지를 조회하고, 결과를 혼합하여 반환하는 엔드포인트.
    """

    try:
        # DB 연결 시작
        connection = pymysql.connect(**db_config)

        # Step 1: 최근 사용자 입력 데이터 가져오기
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user_selection ORDER BY id DESC LIMIT 1")
            user_data = cursor.fetchone()

            # user_selection 테이블에서 데이터가 없는 경우 처리
            if not user_data:
                return render_template('result.html', result=[], error="사용자 입력 데이터가 없습니다. 데이터를 추가해주세요.")

            lunch_selected = user_data['lunch'] == 1
            dinner_selected = user_data['dinner'] == 1
            tourist_count = user_data['tourist_sites_count']

            # 결과 저장 변수 초기화 (점심, 저녁, 관광지)
            lunch, dinner = None, None
            attractions = []

            # Step 2: 점심 데이터 가져오기 (선택된 경우만)
            if lunch_selected:
                cursor.execute("SELECT name, location AS address FROM food_location ORDER BY RAND() LIMIT 1")
                lunch_data = cursor.fetchone()
                if lunch_data:
                    lunch = {
                        "name": lunch_data['name'],
                        "type": "점심",
                        "address": lunch_data['address'],
                        "duration": 1  # 점심 소요 시간을 1시간으로 설정 (임시값, 변경 가능)
                    }

            # Step 3: 저녁 데이터 가져오기 (선택된 경우만)
            if dinner_selected:
                if lunch:  # 점심과 겹치지 않는 데이터를 선택
                    cursor.execute(
                        "SELECT name, location AS address FROM food_location WHERE name != %s ORDER BY RAND() LIMIT 1",
                        (lunch["name"],)
                    )
                else:  # 점심이 없을 경우, 자유롭게 랜덤으로 저녁 데이터 선택
                    cursor.execute("SELECT name, location AS address FROM food_location ORDER BY RAND() LIMIT 1")

                dinner_data = cursor.fetchone()
                if dinner_data:
                    dinner = {
                        "name": dinner_data['name'],
                        "type": "저녁",
                        "address": dinner_data['address'],
                        "duration": 1  # 저녁 소요 시간을 1시간으로 설정 (임시값, 변경 가능)
                    }

            # Step 4: 관광지 데이터 가져오기
            if tourist_count > 0:
                cursor.execute("SELECT name, location AS address FROM tourist_attraction ORDER BY RAND() LIMIT %s",
                               (tourist_count,))
                attractions = [
                    {
                        "name": row['name'],
                        "type": "관광지",
                        "address": row['address'],
                        "duration": random.randint(1, 2)  # 관광지 소요 시간 (1~2시간, 임시값)
                    }
                    for row in cursor.fetchall()
                ]

        # Step 5: 결과 섞기
        result_list = []

        if lunch:
            result_list.append(lunch)  # 점심은 항상 첫 번째
        if attractions:
            result_list.extend(attractions)  # 관광지를 중간에 추가
        if dinner:
            result_list.append(dinner)  # 저녁은 항상 마지막

        # 섞는 로직: 점심은 첫 번째, 저녁은 마지막, 관광지 중 일부는 중간 삽입
        if lunch and dinner and attractions:
            # 점심과 저녁 사이 시간 간격 설정 (6~8 시간 랜덤 값, 임시값)
            lunch_to_dinner_gap = random.randint(6, 8)

            # 점심과 저녁 사이에 관광지 하나 추가
            final_result = [result_list[0]]  # 점심
            if attractions:
                final_result.append(attractions.pop(0))  # 점심 뒤에 관광지 추가
            final_result.extend(attractions)  # 나머지 관광지
            final_result.append(result_list[-1])  # 저녁
        else:
            lunch_to_dinner_gap = None  # 간격 없음
            final_result = result_list

        # 결과 렌더링
        return render_template('result.html', result=final_result, lunch_to_dinner_gap=lunch_to_dinner_gap)

    except Exception as e:
        print(f"오류 발생: {e}")
        return "데이터 처리 중 오류가 발생했습니다."

    finally:
        # DB 연결 종료
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
