from flask import Flask, render_template, request, jsonify, redirect, url_for
import pymysql

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
    """
    메인 페이지
    """
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    """
    관광지 검색 요청 처리
    """
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    # 입력 데이터 검증
    if not city or city == "none":
        return "도시를 선택하세요!", 400
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    # 결과 화면으로 리다이렉트
    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    """
    관광지 검색 결과 화면
    """
    city = request.args.get('city')
    count = request.args.get('count')

    return render_template('result.html', city=city, count=count)


@app.route('/get_categories', methods=['GET'])
def get_categories():
    """
    DB에서 카테고리 목록 가져오는 API
    """
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
            sql = "SELECT id, name, category, location FROM tourist_attraction WHERE city LIKE %s"
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                # 각 카테고리에 대해 LIKE 조건 추가
                like_conditions = []
                for category in category_list:
                    like_conditions.append("name LIKE %s")
                    params.append(f"%{category}%")

                sql += " AND (" + " OR ".join(like_conditions) + ")"

            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

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


if __name__ == '__main__':
    app.run(debug=True)
