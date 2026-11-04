import os
import jwt
from fastapi import Header, HTTPException

from ......shared.infrastructure.messaging.rabbitmq import json_rpc, BrokerUnavailable

class RabbitJWKClient(jwt.PyJWKClient):
    def fetch_data(self):
        try:
            status,data=json_rpc('identity','/api/auth/jwks')
            if status!=200:raise BrokerUnavailable()
            if self.jwk_set_cache is not None:self.jwk_set_cache.put(data)
            return data
        except BrokerUnavailable:
            raise jwt.PyJWKClientConnectionError('Identity broker unavailable')
keys=RabbitJWKClient('http://identity:8080/api/auth/jwks',timeout=3)

def authorized(authorization: str = Header(default='')):
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Inicia sesión para continuar.')
    token = authorization[7:]
    try:
        key = keys.get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=['ES256'], audience='hydrosmart-api',
                            issuer=os.environ['JWT_ISSUER'], options={'require':['exp','sub','iat']})
        if not claims['sub'] or claims.get('profile_type') not in ('propietario','inquilino'):
            raise jwt.InvalidTokenError()
        from urllib.parse import quote
        status,_=json_rpc('identity','/internal/v1/users/'+quote(claims['sub'],safe=''),internal=True)
        if status==404:raise HTTPException(401,'La cuenta ya no está activa.')
        if status!=200:raise HTTPException(503,'Identidad no disponible.')
        return token, claims
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, 'Identidad no disponible.')
    except jwt.PyJWTError:
        raise HTTPException(401, 'La sesión venció.')
