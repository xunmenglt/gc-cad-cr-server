import requests
from urllib.parse import urljoin, urlencode

class APIClient:
    def __init__(self, base_url):
        """
        初始化 API 客户端
        :param base_url: API 的基础地址
        """
        self.base_url = base_url

    def send_request(self, method, endpoint, headers=None, params=None, data=None, files=None):
        """
        通用请求方法
        :param method: HTTP 方法 (GET, POST, PUT, DELETE)
        :param endpoint: API 接口地址
        :param headers: 请求头
        :param params: 查询参数
        :param data: 请求体
        :param files: 上传文件
        :return: 响应数据
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                files=files
            )
            response.encoding="utf-8"
            response.raise_for_status()
            return response.json()  # 返回 JSON 格式响应
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def create_request_url(self, endpoint, query_params={}):
        url = f"{self.base_url}{endpoint}"
        params=urlencode(query_params)
        # params="&".join([f"{k}={v}" for k,v in query_params.items()])
        if params:
            url=url+"?"+params
        return url

    def download_image(self,url, save_path):
        """
        从指定 URL 下载图片并保存到本地路径
        :param url: 图片的 URL
        :param save_path: 保存图片的本地路径
        """
        try:
            # 发送 GET 请求
            response = requests.get(url)
            response.raise_for_status()  # 确保请求成功

            # 以二进制写模式打开一个文件，保存图片
            with open(save_path, 'wb') as file:
                file.write(response.content)
        except requests.RequestException as e:
            print(f"下载图片时出错: {e}")