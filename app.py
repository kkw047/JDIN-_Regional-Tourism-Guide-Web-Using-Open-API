from flask import Flask, render_template, request, redirect, url_for
import pymysql

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

###
# 홈 라우트 (index.html 렌더링)
@app.route('/')
def homepage():
    return render_template('index.html')


# 사용자 입력 데이터 처리 및 DB 저장
@app.route('/submit', methods=['POST'])
def submit():
    lunch = request.form.get('lunch', '0')  # 점심 여부
    dinner = request.form.get('dinner', '0')  # 저녁 여부
    tourist_sites_count = request.form.get('tourist_sites_count', '1')  # 관광지 수

    # 데이터베이스 저장
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

    # 저장 후 결과 페이지로 리다이렉트
    return redirect(url_for('result'))


@app.route('/result')
def result():
    try:
        connection = pymysql.connect(**db_config)

        with connection.cursor() as cursor:
            # 최근 입력된 사용자 데이터 조회
            cursor.execute("SELECT * FROM user_selection ORDER BY id DESC LIMIT 1")
            user_data = cursor.fetchone()

            # 점심/저녁 장소 및 관광지
            lunch = dinner = None
            cursor.execute("SELECT name FROM food_location ORDER BY RAND() LIMIT 1")
            if user_data['lunch'] == '1':
                lunch = cursor.fetchone()['name']
            if user_data['dinner'] == '1':
                dinner = cursor.fetchone()['name']

            cursor.execute("SELECT name FROM tourist_attraction ORDER BY RAND() LIMIT %s",
                           (user_data['tourist_sites_count'],))
            attractions = [row['name'] for row in cursor.fetchall()]

        return render_template('result.html', lunch=lunch, dinner=dinner, attractions=attractions)
    finally:
        connection.close()





if __name__ == '__main__':
    app.run(debug=True)
