import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_rota_inicial():
    async def consultar_rota():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get("/")

    response = asyncio.run(consultar_rota())

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
