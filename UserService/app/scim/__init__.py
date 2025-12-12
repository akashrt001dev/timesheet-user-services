# app/scim/__init__.py
# This file can be used to aggregate SCIM routers
from fastapi import APIRouter

scim_router = APIRouter()

# TODO: Add SCIM endpoints when UserHandler and GroupHandler routers are implemented
# scim_router.include_router(UserHandler.router)
# scim_router.include_router(GroupHandler.router)