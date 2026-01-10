# add_latency.py
# Ajouter ce middleware à votre FastAPI pour simuler des conditions réelles

import asyncio
import random
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

class LatencySimulatorMiddleware(BaseHTTPMiddleware):
    """
    Simule la latence d'une base de données ou d'un service externe
    pour rendre les tests plus réalistes
    """
    async def dispatch(self, request: Request, call_next):
        # Simuler une latence réseau/DB réaliste
        # 10-50ms pour simuler une DB PostgreSQL sur le réseau
        latency = random.uniform(0.01, 0.05)  # 10-50ms
        
        # Pour simuler des appels API externes lents (optionnel)
        # latency = random.uniform(0.1, 0.3)  # 100-300ms
        
        await asyncio.sleep(latency)
        
        response = await call_next(request)
        return response

# Dans votre web.py, ajoutez :
# app.add_middleware(LatencySimulatorMiddleware)