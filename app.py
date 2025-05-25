from flask import Flask, render_template, request, jsonify, redirect, url_for
import pymysql
import random
import string
from urllib.parse import unquote
import json
import sys  # submit_review에서 사용

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
    connection = None
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
        if connection and connection.open:
            connection.close()


@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT id, name, address, mapx, mapy, image, category FROM tourist_attraction WHERE address LIKE %s"
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category_item in category_list:
                    like_conditions.append("category LIKE %s")
                    params.append(f"%{category_item}%")  # category -> category_item

                sql += " AND (" + " OR ".join(like_conditions) + ")"

            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            for res_item in results:  # result -> res_item
                res_item['location'] = {'mapx': res_item['mapx'], 'mapy': res_item['mapy']}

        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/process')
def process():
    city = request.args.get('city')
    count_str = request.args.get('count')  # count -> count_str
    try:
        count = int(count_str)  # count_str 사용
    except ValueError:
        return "잘못된 count 값입니다.", 400

    site_data = {}
    for i in range(1, count + 1):
        location_str = request.args.get(f'site{i}_location')
        location = {}  # 기본값 초기화
        if location_str:
            try:
                location_str_decoded = unquote(location_str)  # unquote(location_str)
                location = json.loads(location_str_decoded)  # location_str_decoded
            except json.JSONDecodeError:
                print(f"Warning: JSONDecodeError for site{i}_location: {location_str}")
                location = {}
        # else: location은 이미 {}로 초기화됨

        site_data[i] = {
            'name': request.args.get(f'site{i}_name'),
            'location': location,
            'image': request.args.get(f'site{i}_image'),
            'address': request.args.get(f'site{i}_address'),
            'id': request.args.get(f'site{i}_id')
        }

    return render_template('process.html', city=city, count=count, site_data=site_data)


@app.route('/live', methods=['GET'])
def live_redirect():
    usercode = request.args.get('code')
    if not usercode:
        return "사용자 코드가 필요합니다.", 400
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
                SELECT tourist_site_1, tourist_site_2, tourist_site_3
                FROM user_travel_data
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            row = cursor.fetchone()
            print("row:", row)

            if not row:
                return "잘못된 사용자 코드입니다.", 404

            determined_count = 0  # count -> determined_count
            for i in range(1, 4):
                if row.get(f'tourist_site_{i}') is not None:
                    determined_count += 1
                else:
                    break

            if determined_count == 0:
                return "선택된 관광지가 없습니다.", 400

            # count가 3을 초과하지 않도록 하는 로직은 여기서 불필요해 보임
            # live_with_usercode로 전달되는 count는 실제 저장된 사이트 수를 반영해야 함.
            # 현재 로직은 최대 3개까지만 확인하므로 determined_count를 그대로 사용.

            return redirect(url_for('live_with_usercode', usercode=usercode, count=determined_count))
    except Exception as e:
        print(f"Error in live_redirect: {e}")
        return "오류 발생!", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/live', methods=['POST'])
def live():
    city = request.form.get('city')
    count_str = request.form.get('count')

    try:
        count = int(count_str)
        if not (1 <= count <= 5):  # Ensure count is within a reasonable range, e.g., 1-5
            return "관광지 개수는 1~5개여야 합니다.", 400
    except ValueError:
        return "잘못된 count 값입니다.", 400

    usercode = ''
    # usercode 생성 및 중복 확인
    # DB 연결은 필요한 시점에 최소한으로 유지
    while True:
        usercode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            db_conn_outer = pymysql.connect(**db_config)
            with db_conn_outer.cursor() as cursor:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    break
        except Exception as e:
            print(f"usercode 중복 확인 오류: {e}")
            # 이 에러는 심각하므로, 재시도하거나 에러 응답을 반환하는 로직 고려
            return "사용자 코드 생성 중 오류가 발생했습니다.", 500
        finally:
            if db_conn_outer and db_conn_outer.open:
                db_conn_outer.close()

    tourist_sites_ids_from_form = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites_ids_from_form.append(site_id)
    print(f"DEBUG: 폼에서 받은 관광지 ID 목록: {tourist_sites_ids_from_form}")

    missions = []

    db_conn_inner = None
    try:
        db_conn_inner = pymysql.connect(**db_config)
        with db_conn_inner.cursor() as cursor:
            # 모든 미션을 미리 한 번 조회하여 성능 최적화
            cursor.execute("SELECT id, category FROM mission")
            all_missions = cursor.fetchall()
            print(f"DEBUG: 데이터베이스에서 조회된 모든 미션: {all_missions}")

            # 모든 미션의 카테고리를 미리 정규화하여 딕셔너리로 저장 (성능 개선)
            normalized_all_mission_categories = {}
            for mission_data in all_missions:
                mission_id = mission_data['id']
                raw_mission_category = mission_data['category']
                if raw_mission_category:
                    # 쉼표로 분리 후 각 요소의 앞뒤 공백 제거 및 소문자 변환
                    normalized_categories = {cat.strip().lower() for cat in raw_mission_category.split(',') if
                                             cat.strip()}
                    normalized_all_mission_categories[mission_id] = normalized_categories
                else:
                    normalized_all_mission_categories[mission_id] = set()  # 카테고리가 없으면 빈 집합

            print(f"DEBUG: 정규화된 모든 미션 카테고리 맵: {normalized_all_mission_categories}")

            for i in range(count):  # count는 1부터 시작하므로 인덱스는 0부터 count-1
                site_id = tourist_sites_ids_from_form[i]  # 폼에서 받은 ID 사용

                mission_id_to_add = None
                if site_id:
                    # 1. 관광지의 카테고리 가져오기
                    cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                    site_category_result = cursor.fetchone()

                    if site_category_result and site_category_result['category']:
                        raw_site_category = site_category_result['category']
                        # 2. 관광지 카테고리 정규화 (쉼표 분리, 공백 제거, 중복 제거)
                        # `'`가 없더라도 split(',')은 작동하며, 단일 카테고리('문화존')도 잘 처리함.
                        site_categories = {cat.strip().lower() for cat in raw_site_category.split(',') if
                                           cat.strip()}
                        print(
                            f"DEBUG: 관광지 ID: {site_id}, 원본 카테고리: '{raw_site_category}', 정규화된 관광지 카테고리 (집합): {site_categories}")

                        # 4. 매칭되는 미션 찾기
                        matching_missions = []
                        for mission_data in all_missions:  # 미리 가져온 all_missions 사용
                            mission_id = mission_data['id']
                            mission_categories = normalized_all_mission_categories.get(mission_id, set())

                            # 관광지 카테고리와 미션 카테고리가 하나라도 겹치면 선택
                            if site_categories and (
                                    site_categories & mission_categories):  # site_categories가 비어있지 않아야 교집합 검사
                                matching_missions.append(mission_id)
                                # print(f"DEBUG: 미션 ID {mission_id} ({mission_categories}) 매칭됨! (관광지: {site_categories})") # 너무 많을 경우 주석 처리

                        print(f"DEBUG: 관광지 {site_id}에 대해 매칭된 미션 목록: {matching_missions}")

                        # 5. 매칭된 미션이 있으면 랜덤 선택, 없으면 전체에서 랜덤
                        if matching_missions:
                            mission_id_to_add = random.choice(matching_missions)
                            print(f"DEBUG: 관광지 {site_id}에 특정 카테고리 매칭 미션 할당: {mission_id_to_add}")
                        else:
                            if all_missions:  # all_missions가 비어있지 않은 경우에만 랜덤 선택
                                mission_id_to_add = random.choice([m['id'] for m in all_missions])
                                print(f"DEBUG: 관광지 {site_id}에 매칭되는 미션 없음, 전체 미션 중 랜덤 할당: {mission_id_to_add}")
                            else:
                                print(f"DEBUG: 미션 테이블에 미션이 아예 없습니다. 관광지 {site_id}에 미션 할당 불가.")
                                mission_id_to_add = None  # 미션이 아예 없으면 None으로 설정
                    else:
                        print(f"DEBUG: 관광지 ID: {site_id}의 카테고리 정보가 없거나 비어있습니다. 미션 할당 없음.")
                        mission_id_to_add = None  # 카테고리 정보가 없으면 미션 없음
                else:
                    print(f"DEBUG: site_id가 None입니다. 미션 할당 없음.")
                    mission_id_to_add = None  # site_id 자체가 None인 경우

                missions.append(mission_id_to_add)
    except Exception as e:
        print(f"미션 ID 조회 중 오류: {e}")
        # 오류 발생 시, count 만큼 missions 리스트를 채우기 위해 None 추가
        while len(missions) < count:
            missions.append(None)
    finally:
        if db_conn_inner and db_conn_inner.open:
            db_conn_inner.close()

    # missions 리스트 길이가 count와 일치하도록 패딩 (혹시 모를 경우)
    while len(missions) < count:
        print(f"DEBUG: missions 리스트 길이 보충 중. 현재 길이: {len(missions)}, 목표: {count}")
        missions.append(None)

    # tourist_sites_ids_from_form 리스트 길이 보충 (DB 삽입을 위해)
    while len(tourist_sites_ids_from_form) < count:
        tourist_sites_ids_from_form.append(None)

    print(f"DEBUG: 최종 할당된 미션 목록 (DB 삽입 전): {missions}")
    print(f"DEBUG: 최종 관광지 ID 목록 (DB 삽입 전): {tourist_sites_ids_from_form}")

    # Database insertion logic... (이 부분은 변경 없음)
    db_conn_insert = None
    try:
        db_conn_insert = pymysql.connect(**db_config)
        with db_conn_insert.cursor() as cursor:
            ts_cols = [f"tourist_site_{i}" for i in range(1, count + 1)]
            m_cols = [f"mission_{i}" for i in range(1, count + 1)]
            m_conf_cols = [f"mission_{i}_confirmed" for i in range(1, count + 1)]
            ts_conf_cols = [f"tourist_site_{i}_confirmed" for i in range(1, count + 1)]
            r_conf_cols = [f"route_{i}_confirmed" for i in range(1, count)] if count > 1 else []

            all_columns_list = ts_cols + m_cols + m_conf_cols + ts_conf_cols + r_conf_cols
            columns_sql_segment = ", ".join(all_columns_list)
            placeholders_sql_segment = ", ".join(["%s"] * len(all_columns_list))

            sql = f"""
                INSERT INTO user_travel_data (usercode, {columns_sql_segment}) 
                VALUES (%s, {placeholders_sql_segment})
            """

            values_for_tourist_sites = tourist_sites_ids_from_form[:count]
            values_for_missions = missions[:count]

            initial_mission_confirmed_values = [0] * count
            initial_site_confirmed_values = ([2] + [0] * (count - 1)) if count > 0 else []
            initial_route_confirmed_values = [0] * (count - 1) if count > 1 else []

            params = ([usercode] +
                      values_for_tourist_sites +
                      values_for_missions +
                      initial_mission_confirmed_values +
                      initial_site_confirmed_values +
                      initial_route_confirmed_values)

            print(f"DEBUG: 삽입할 SQL: {sql}")
            print(f"DEBUG: 삽입할 파라미터 (usercode, sites, missions, mission_conf, site_conf, route_conf): {params}")
            print(f"DEBUG: 파라미터 길이: {len(params)}, 예상 플레이스홀더 길이: {1 + len(all_columns_list)}")

            if len(params) != (1 + len(all_columns_list)):
                print("CRITICAL DEBUG: 파라미터 개수 불일치!")
                return "서버 내부 오류: 파라미터 개수 불일치.", 500

            cursor.execute(sql, params)
            db_conn_insert.commit()
            print(f"DEBUG: 사용자 코드 {usercode}에 대한 데이터 삽입 완료")
    except pymysql.MySQLError as e_db_insert:
        print(f"데이터베이스 삽입 오류: {e_db_insert}")
        if db_conn_insert and db_conn_insert.open: db_conn_insert.rollback()
        return "오류 발생 (DB 삽입 실패)!", 500
    except Exception as e_insert:
        print(f"일반 삽입 오류: {e_insert}")
        if db_conn_insert and db_conn_insert.open: db_conn_insert.rollback()
        return "오류 발생 (삽입 실패)!", 500
    finally:
        if db_conn_insert and db_conn_insert.open:
            db_conn_insert.close()

    return redirect(url_for('live_with_usercode', usercode=usercode, count=count))
@app.route('/live/<usercode>', methods=['GET'])
def live_with_usercode(usercode):
    count = int(request.args.get('count', 0))
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            if count == 0:  # count가 0이면 여기서 처리
                # usercode로 조회하여 실제 count를 다시 결정할 수도 있음
                # 여기서는 일단 에러로 처리하거나, count를 다시 조회하는 로직 추가 가능
                return "선택된 관광지가 없습니다. (count=0)", 400

            site_columns = [f'tourist_site_{i}' for i in range(1, count + 1)]
            mission_columns = [f'mission_{i}' for i in range(1, count + 1)]
            # mission_X_confirmed 컬럼도 필요하면 여기에 추가
            mission_confirmed_columns = [f'mission_{i}_confirmed' for i in range(1, count + 1)]
            site_status_columns = [f'tourist_site_{i}_confirmed' for i in range(1, count + 1)]

            route_columns = []
            if count > 1:
                route_columns = [f'route_{i}_confirmed' for i in range(1, count)]

            all_columns = site_columns + mission_columns + mission_confirmed_columns + site_status_columns + route_columns

            sql = f"""
                SELECT {', '.join(all_columns)}
                FROM user_travel_data 
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return "잘못된 사용자 코드입니다.", 404

            tourist_sites = []
            for i in range(1, count + 1):
                site_id = user_data.get(f'tourist_site_{i}')
                if site_id:
                    sql_site = "SELECT id, name, address, mapx, mapy, image FROM tourist_attraction WHERE id = %s"
                    cursor.execute(sql_site, (site_id,))
                    site_info = cursor.fetchone()
                    if site_info:
                        tourist_sites.append(site_info)
                    else:
                        tourist_sites.append(None)  # ID는 있지만 정보가 없는 경우
                else:
                    tourist_sites.append(None)  # ID 자체가 없는 경우

            markers = []
            statuses = []  # 관광지 상태
            for i, site in enumerate(tourist_sites):
                if site:  # site가 None이 아닌 경우에만 처리
                    status = user_data.get(f'tourist_site_{i + 1}_confirmed', 0)
                    markers.append({
                        'name': site['name'],
                        'mapx': float(site['mapx']) if site.get('mapx') else 0.0,  # mapx, mapy float 변환 및 None 체크
                        'mapy': float(site['mapy']) if site.get('mapy') else 0.0,
                        'status': status,
                        'site_number': i + 1
                    })
                    statuses.append(status)
                else:  # site가 None인 경우, 관련 데이터도 None 또는 기본값으로 채움
                    statuses.append(None)  # 또는 적절한 기본값

            routes = []
            if count > 1:
                for i in range(1, count):
                    route_status = user_data.get(f'route_{i}_confirmed', 0)
                    routes.append({
                        'status': route_status,
                        'route_number': i
                    })

            # live.html에 전달할 미션 데이터 및 미션 완료 상태
            missions_live = [user_data.get(f'mission_{i}') for i in range(1, count + 1)]
            mission_statuses_live = [bool(user_data.get(f'mission_{i}_confirmed', 0)) for i in range(1, count + 1)]

        # 실제 유효한 tourist_sites의 개수로 count를 다시 설정하여 템플릿에 전달
        valid_sites_count = len([s for s in tourist_sites if s is not None])

        return render_template(
            'live.html',
            usercode=usercode,
            tourist_sites=tourist_sites,  # None 포함될 수 있음
            missions=missions_live,  # mission ID 목록
            mission_statuses=mission_statuses_live,  # mission 완료 상태 목록
            markers=markers,
            statuses=statuses,  # 관광지 상태 목록
            routes=routes,
            count=valid_sites_count
        )
    except Exception as e:
        print(f"오류 발생 (live_with_usercode): {e}")
        return "오류 발생!", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/mission')
def mission_page():
    usercode = request.args.get('usercode')
    return render_template('mission.html', usercode=usercode)

@app.route('/get_mission_details/<usercode>', methods=['GET'])
def get_mission_details(usercode):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 미션 데이터와 함께 관광지 ID 가져오기
            sql = """
                SELECT
                    mission_1, mission_1_confirmed, tourist_site_1,
                    mission_2, mission_2_confirmed, tourist_site_2,
                    mission_3, mission_3_confirmed, tourist_site_3
                FROM user_travel_data
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return jsonify({"success": False, "error": "사용자 데이터를 찾을 수 없습니다."}), 404

            missions_data = []
            for i in range(1, 4): # 최대 3개의 미션/관광지 가정
                mission_id_key = f'mission_{i}'
                mission_confirmed_key = f'mission_{i}_confirmed'
                tourist_site_id_key = f'tourist_site_{i}' # 관광지 ID를 위한 새로운 키

                mission_id = user_data.get(mission_id_key)
                mission_confirmed_status = user_data.get(mission_confirmed_key)
                is_mission_confirmed = bool(mission_confirmed_status) if mission_confirmed_status is not None else False
                tourist_site_id = user_data.get(tourist_site_id_key) # 관광지 ID 가져오기

                site_info_to_add = { # 기본값으로 초기화
                    "site_name": "정보 없음",
                    "site_image": None # 기본 이미지 또는 플레이스홀더
                }

                if tourist_site_id: # 연결된 관광지가 있는 경우
                    cursor.execute("SELECT name, image FROM tourist_attraction WHERE id = %s", (tourist_site_id,))
                    site_details = cursor.fetchone()
                    if site_details:
                        site_info_to_add["site_name"] = site_details['name']
                        site_info_to_add["site_image"] = site_details['image']

                if mission_id:
                    cursor.execute("SELECT id, title, content FROM mission WHERE id = %s", (mission_id,))
                    mission_info = cursor.fetchone()

                    if mission_info:
                        missions_data.append({
                            "id": mission_info['id'],
                            "title": mission_info['title'],
                            "content": mission_info['content'],
                            "confirmed": is_mission_confirmed,
                            "mission_number": i,
                            "site_name": site_info_to_add["site_name"], # 관광지 이름 추가
                            "site_image": site_info_to_add["site_image"] # 관광지 이미지 추가
                        })
                    else:
                        # user_travel_data에는 미션 ID가 있지만, mission 테이블에는 없는 경우
                        missions_data.append({
                            "id": None,
                            "title": "미션 정보를 찾을 수 없습니다.",
                            "content": "",
                            "confirmed": is_mission_confirmed,
                            "mission_number": i,
                            "site_name": site_info_to_add["site_name"],
                            "site_image": site_info_to_add["site_image"]
                        })
                elif tourist_site_id:
                    # 이 경우는 해당 슬롯에 관광지가 선택되었지만, 미션이 할당되지 않았음을 의미합니다.
                    # 미션 없이 관광지 정보만 표시하려면 여기에 항목을 추가할 수 있습니다.
                    # 현재는 "미션"인 항목만 표시하기 위해 이 부분에서 미션 항목을 엄격하게 생성하지 않습니다.
                    # mission_id가 없을 경우 None을 추가하는 원래 로직과의 일관성을 위해:
                    missions_data.append(None)
                else: # 해당 슬롯에 mission_id와 tourist_site_id 모두 없는 경우
                    missions_data.append(None)
            return jsonify({"success": True, "missions": missions_data})
    except Exception as e:
        print(f"사용자 코드 {usercode}에 대한 미션 상세 정보 가져오기 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()

@app.route('/update_mission_status', methods=['POST'])
def update_mission_status():
    data = request.get_json()
    usercode = data.get('usercode')
    mission_number = data.get('mission_number')
    is_confirmed = data.get('confirmed')

    if not all([usercode, mission_number is not None, is_confirmed is not None]):
        return jsonify({"success": False, "error": "필수 파라미터가 누락되었습니다."}), 400

    if not isinstance(mission_number, int) or not (1 <= mission_number <= 3):
        return jsonify({"success": False, "error": "잘못된 mission_number 값입니다."}), 400

    confirmed_value = 1 if is_confirmed else 0
    mission_confirmed_column = f'mission_{mission_number}_confirmed'
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET {mission_confirmed_column} = %s WHERE usercode = %s"
            cursor.execute(sql, (confirmed_value, usercode))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({"success": True, "message": "미션 상태가 업데이트되었습니다."})
            else:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    return jsonify({"success": False, "error": "해당 usercode를 찾을 수 없습니다."}), 404
                return jsonify(
                    {"success": True, "message": "미션 상태가 이미 해당 값으로 설정되어 있거나 변경 사항이 없습니다."})  # 오타 수정: 없습습니다 -> 없습니다
    except pymysql.MySQLError as e:
        print(f"DB 오류 (미션 상태 업데이트): {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({"success": False, "error": f"데이터베이스 오류: {str(e)}"}), 500
    except Exception as e:
        print(f"미션 상태 업데이트 중 일반 오류: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    usercode = data.get('usercode')  # data['usercode'] -> data.get('usercode')
    site_number = data.get('site_number')  # data['site_number'] -> data.get('site_number')
    new_status = data.get('new_status')  # data['new_status'] -> data.get('new_status')

    if not all([usercode, site_number, new_status is not None]):  # 필수 파라미터 체크
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET tourist_site_{site_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()
            if cursor.rowcount > 0:
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404

    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/update_cancel', methods=['POST'])
def update_cancel():
    data = request.json
    usercode = data.get('usercode')  # data['usercode'] -> data.get('usercode')
    item_type = data.get('item_type')  # data['item_type'] -> data.get('item_type')
    item_number_str = data.get('item_number')  # data['item_number'] -> data.get('item_number')

    if not all([usercode, item_type, item_number_str]):
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    try:
        item_number = int(item_number_str)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'item_number는 정수여야 합니다.'}), 400

    status_sequence = [
        'tourist_site_1_confirmed',
        'route_1_confirmed',
        'tourist_site_2_confirmed',
        'route_2_confirmed',
        'tourist_site_3_confirmed'
        # 필요에 따라 4, 5번 사이트/경로 추가
    ]
    connection = None
    cursor = None  # try 블록 밖에서 선언
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        current_index = -1
        # status_sequence에 없는 item_number가 들어올 경우를 대비한 유효성 검사
        max_site_num = 0
        max_route_num = 0
        for s in status_sequence:
            if "tourist_site_" in s:
                num = int(s.split("_")[2])
                if num > max_site_num: max_site_num = num
            elif "route_" in s:
                num = int(s.split("_")[1])
                if num > max_route_num: max_route_num = num

        if item_type == 'site' and not (1 <= item_number <= max_site_num):
            return jsonify({'status': 'error', 'message': f'잘못된 site_number: {item_number}'}), 400
        if item_type == 'route' and not (1 <= item_number <= max_route_num):
            return jsonify({'status': 'error', 'message': f'잘못된 route_number: {item_number}'}), 400

        for i, status_col_name in enumerate(status_sequence):  # status -> status_col_name
            if item_type == 'site' and status_col_name.startswith(f'tourist_site_{item_number}_confirmed'):
                current_index = i
                break
            elif item_type == 'route' and status_col_name.startswith(f'route_{item_number}_confirmed'):
                current_index = i
                break

        if current_index == -1:  # 매칭되는 항목이 없는 경우
            return jsonify({'status': 'error', 'message': '취소할 항목을 찾을 수 없습니다.'}), 404

        if current_index != -1:
            updates = []
            for i, status_col_name_update in enumerate(status_sequence):  # status -> status_col_name_update
                if i == current_index:
                    updates.append(f"{status_col_name_update} = 2")  # 진행중
                elif i > current_index:
                    updates.append(f"{status_col_name_update} = 0")  # 대기

            if updates:
                sql = f"""UPDATE user_travel_data 
                         SET {', '.join(updates)}
                         WHERE usercode = %s"""
                cursor.execute(sql, (usercode,))
                connection.commit()
                if cursor.rowcount > 0:
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404
            else:  # updates 리스트가 비어있는 경우 (예: 마지막 항목 취소 시)
                return jsonify({'status': 'success', 'message': '변경할 후속 상태가 없습니다.'})

        return jsonify({'status': 'success'})  # 이 부분은 current_index != -1 블록 안으로 이동했어야 함.

    except Exception as e:
        print(f"Error in update_cancel: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        if cursor:  # cursor가 None이 아닐 때만 close
            cursor.close()
        if connection and connection.open:
            connection.close()


@app.route('/update_route_status', methods=['POST'])
def update_route_status():
    data = request.get_json()
    usercode = data.get('usercode')
    route_number = data.get('route_number')
    new_status = data.get('new_status')

    if not all([usercode, route_number, new_status is not None]):
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET route_{route_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404

    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/review/<usercode>')
def review_page(usercode):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM user_travel_data WHERE usercode = %s", (usercode,))  # SQL 인젝션 방지 위해 %s 사용
            user_data = cursor.fetchone()

            if not user_data:
                return "여행 데이터가 존재하지 않습니다.", 404

            selected_site_ids = []
            for i in range(1, 6):  # 최대 5개 관광지 가정 (user_travel_data 스키마에 맞게 조정)
                site_key = f'tourist_site_{i}'
                if site_key in user_data and user_data[site_key]:
                    selected_site_ids.append(user_data[site_key])
                # else: 더 이상 tourist_site_X 컬럼이 없으면 중단 (선택적)
                #    break

        sites_to_review = []
        if selected_site_ids:  # ID가 있을 때만 상세 정보 조회
            for site_id in selected_site_ids:
                site_details = get_site_details_by_id(site_id)  # 이 함수는 내부적으로 DB 연결을 열고 닫음
                if site_details:
                    sites_to_review.append(site_details)

        return render_template('review.html', usercode=usercode, sites_to_review=sites_to_review)

    except Exception as e:
        print(f"Error in review_page for usercode {usercode}: {e}")
        return "후기 페이지를 불러오는 중 오류가 발생했습니다.", 500
    finally:
        if connection and connection.open:  # 'connection'이 정의되었는지 확인
            connection.close()


@app.route('/submit_review', methods=['POST'])
def submit_review():
    usercode = request.form.get('usercode')
    MAX_REVIEW_LENGTH = 300
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            for key, value in request.form.items():
                if key.startswith('review_text_'):
                    site_id_str = key.replace('review_text_', '')  # site_id -> site_id_str
                    # site_id가 숫자인지 확인 (선택적이지만 권장)
                    try:
                        site_id = int(site_id_str)
                    except ValueError:
                        print(f"Warning: Invalid site_id format {site_id_str} in review form.", file=sys.stderr)
                        continue  # 다음 항목으로 건너뛰기

                    review_content = value

                    if review_content and len(review_content) > MAX_REVIEW_LENGTH:
                        review_content = review_content[:MAX_REVIEW_LENGTH]
                        print(f"Warning: Review for site {site_id} truncated to {MAX_REVIEW_LENGTH} characters.",
                              file=sys.stderr)

                    rating_str = request.form.get(f'rating_{site_id}')
                    rating_value = 3

                    if rating_str:
                        try:
                            int_val = int(rating_str)
                            if 1 <= int_val <= 5:
                                rating_value = int_val
                        except ValueError:
                            pass

                    if site_id and (review_content or rating_value is not None):  # rating_value가 None이 아닌지 명시적 확인
                        sql = """
                           INSERT INTO review (tourist_attraction_id, content, rating, usercode)
                           VALUES (%s, %s, %s, %s) 
                           """  # usercode도 함께 저장 (선택 사항, 테이블 스키마에 따라)
                        # usercode를 저장하지 않는다면 VALUES (%s, %s, %s)
                        # params = (site_id, review_content, rating_value, usercode) 또는 (site_id, review_content, rating_value)
                        cursor.execute(sql, (site_id, review_content, rating_value, usercode))  # usercode 추가 가정
            connection.commit()

        return redirect(url_for('finished'))

    except Exception as e:
        print(f"Error submitting review for usercode {usercode}: {e}", file=sys.stderr)
        if connection and connection.open:  # 'connection'이 정의되었는지 확인
            connection.rollback()
        return "후기를 제출하는 중 오류가 발생했습니다.", 500
    finally:
        if connection and connection.open:  # 'connection'이 정의되었는지 확인
            connection.close()


@app.route('/finished')
def finished():
    return render_template('finished.html')


def get_site_details_by_id(site_id):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT id, name, image, address FROM tourist_attraction WHERE id = %s"
            cursor.execute(sql, (site_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching site details for {site_id}: {e}")
        return None
    finally:
        if connection and connection.open:  # 'connection'이 정의되었는지 확인
            connection.close()


if __name__ == '__main__':
    # print("스케줄러가 실행 중입니다...") # 스케줄러 관련 코드가 없으므로 주석 처리 또는 삭제
    app.run(host='0.0.0.0', port=5000, debug=True)