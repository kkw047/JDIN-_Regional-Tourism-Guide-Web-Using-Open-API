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
    메인 페이지: 도시와 관광지 수 선택
    """
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    """
    관광지 검색 요청 처리.
    선택한 도시와 관광지 수를 기반으로 결과 페이지로 리다이렉트.
    """
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    # 기본 값 검증
    if not city or city == "none":
        return "도시를 선택하세요!", 400
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    # result.html로 리다이렉트 (선택된 값 전달)
    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    """
    선택된 도시와 관광지 수를 기반으로 관광지 검색 결과를 렌더링
    """
    city = request.args.get('city')
    count = int(request.args.get('count'))

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 선택된 도시에서 관광지 검색 (최대 count 개)
            sql = """
                SELECT id, name, category, city, location, created_at, updated_at 
                FROM tourist_attraction
                WHERE city = %s
                ORDER BY RAND() LIMIT %s
            """
            cursor.execute(sql, (city, count))
            results = cursor.fetchall()

        return render_template('result.html', results=results, city=city, count=count)
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()


@app.route('/get_categories', methods=['GET'])
def get_categories():
    """
    DB에서 동적 카테고리 목록 가져오기
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


if __name__ == '__main__':
    app.run(debug=True)
