import asyncio

from aiohttp import ClientSession, BasicAuth
from uuid import uuid4
from datetime import datetime
from requests import get
from fake_useragent import UserAgent as ua


INVOICE_CREATE_URL = "https://api.lava.ru/invoice/create"
INVOICE_INFO_URL = 'https://api.lava.ru/invoice/info'
INVOICE_TEST_URL = 'https://api.lava.ru/test/ping'


class JwtAuth(BasicAuth):
    def __init__(self, token: str):
        self.token = token

    def encode(self) -> str:
        return f'{self.token}'


class LavaAPI:
    def __init__(
            self,
            wallet_to: str,
            sum: float,
            jwt_token: str,
            expire: int = 1440,
    ):
        self.wallet_to = wallet_to
        self.sum = float(sum)
        self.order_id = uuid4().hex
        self.expire = expire
        self.expire_datetime: datetime = None
        self.jwt_token = jwt_token
        self.auth = JwtAuth(self.jwt_token)
        # response = get(INVOICE_TEST_URL, headers=self.headers)
        # print(response.request.headers)
        self.session = ClientSession(
            auth=self.auth,
            skip_auto_headers=['Content-Type'],
            # headers={
            #     'User-Agent': ua.chrome
            # }
        )
        print(self.session.headers)
        self.id = None

    async def create_order(self):
        async with self.session as session:
            async with self.session.get(INVOICE_CREATE_URL) as response:
                print(await response.json())
            # print(session.headers)
            data = {
                "wallet_to": self.wallet_to,
                "sum": round(self.sum, 2),
                "order_id": self.order_id,
                "expire": self.expire
            }
            async with session.post(
                INVOICE_CREATE_URL,
                data=data
            ) as response:
                print(response.request_info.headers)
                response = await response.json()
                if response['status'] == 'success':
                    self.id = response['id']
                    self.expire_datetime = datetime.fromtimestamp(float(response['expire']))
                    return response['url']
                else:
                    return response

    async def wait_pay(self):
        data = {
            'id': self.id
        }
        async with self.session as session:
            while datetime.now() < self.expire_datetime:
                async with session.post(
                    INVOICE_INFO_URL,
                    data=data
                ) as response:
                    response_json = await response.json()
                    invoice = response_json['invoice']
                    if invoice['status'] == 'cancel':
                        return False
                    if invoice['status'] == 'success':
                        return True
                await asyncio.sleep(10)
            else:
                return False


if __name__ == '__main__':
    async def main():
        api = LavaAPI(
            wallet_to='R10862914',
            sum=10,
            jwt_token='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOiIxMTIzODM5ZC03NmE1LTBmNTUtNzA1NS00ZjY3MzVjOGMzMDIiLCJ0aWQiOiIwZTM0NDhlNy1hNDg4LTgxOTItOWU4YS1jYmQwYTQxYjNkMjcifQ.zAzBVI8M-qdODtScODXzbK08YIt3lqOy2lelPnr6TO0'
        )
        url = await api.create_order()
        print(url)
        await api.wait_pay()
    import asyncio
    asyncio.run(main())