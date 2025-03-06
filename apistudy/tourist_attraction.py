import requests

def get_tourist_sites():
    #관광지 정보를 가져오는 함수
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'
    url = f'https://api.odcloud.kr/api/3067368/v1/uddi:b9d25b17-9391-471e-9c7f-aad014581edd?page=1&perPage=10-/&serviceKey={service_key}'

    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            '관광지명': item['관광지명'],
            '시군': item['시군'],
            '위치': item['위치']
        })

    return result