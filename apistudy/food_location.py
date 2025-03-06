import requests

def get_Cheongju():
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'
    url = f'https://api.odcloud.kr/api/3033595/v1/uddi:74266317-2cd8-4b3d-8682-d72062ac1743?page=1&perPage=10&serviceKey={service_key}'

    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            '업소명': item['업소명'],
            '위치': item['소재지(지번)'].lstrip('충청북도')
        })

    return result

def get_Chungju():
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'
    url = f'https://api.odcloud.kr/api/3037407/v1/uddi:050eceee-1dde-4be2-ac6b-ef812b73ec8f_201909101500?page=1&perPage=10&serviceKey={service_key}'

    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            '업소명': item['업소명'],
            '위치': item['소재지(도로명)'].lstrip('충청북도')
        })

    return result
