"""
Интеграция с HH.ru API (v3.0.0)
OAuth авторизация и импорт резюме
"""
import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.models import User


class HHIntegration:
    """Сервис интеграции с HeadHunter.ru"""
    
    def __init__(self):
        self.client_id = os.getenv("HH_CLIENT_ID")
        self.client_secret = os.getenv("HH_CLIENT_SECRET")
        self.redirect_uri = os.getenv("HH_REDIRECT_URI", "http://localhost:3000/auth/hh/callback")
        self.api_base_url = "https://api.hh.ru"
        self.auth_base_url = "https://hh.ru/oauth"
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Получение URL для OAuth авторизации"""
        if not self.client_id:
            raise ValueError("HH_CLIENT_ID not configured")
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_base_url}/authorize?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Обмен authorization code на access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("HH credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_base_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to exchange code: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Получение информации о пользователе"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to get user info: {response.text}")
            
            return response.json()
    
    async def get_resumes(self, access_token: str) -> List[Dict[str, Any]]:
        """Получение списка резюме пользователя"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/resumes/mine",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to get resumes: {response.text}")
            
            return response.json().get("items", [])
    
    async def get_resume(self, access_token: str, resume_id: str) -> Dict[str, Any]:
        """Получение детальной информации о резюме"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/resumes/{resume_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to get resume: {response.text}")
            
            return response.json()
    
    async def import_resume_to_user(
        self,
        db: Session,
        user: User,
        resume_data: Dict[str, Any]
    ) -> User:
        """Импорт данных резюме в профиль пользователя"""
        # Импорт личных данных
        if resume_data.get("first_name"):
            if not user.full_name:
                user.full_name = f"{resume_data.get('first_name', '')} {resume_data.get('last_name', '')}".strip()
        
        # Импорт контактов
        contacts = resume_data.get("contacts", {})
        if contacts.get("email") and not user.email:
            user.email = contacts.get("email")
        
        # Импорт опыта работы
        experience = []
        for exp in resume_data.get("experience", []):
            experience.append({
                "company": exp.get("company", ""),
                "position": exp.get("position", ""),
                "start_date": exp.get("start", ""),
                "end_date": exp.get("end"),
                "description": exp.get("description", ""),
                "skills": exp.get("skills", [])
            })
        if experience:
            user.work_experience = experience
        
        # Импорт образования
        education = []
        for edu in resume_data.get("education", {}).get("primary", []):
            education.append({
                "institution": edu.get("name", ""),
                "faculty": edu.get("name", ""),
                "year": edu.get("year", ""),
            })
        if education:
            user.education = education
        
        # Импорт навыков
        skills = resume_data.get("skills", [])
        if skills:
            user.skills = skills
        
        # Сохранение HH метрик
        user.hh_metrics = {
            "profile_views": resume_data.get("views_count", 0),
            "last_activity": resume_data.get("updated_at", ""),
        }
        user.hh_profile_synced_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return user
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Обновление access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("HH credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_base_url}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to refresh token: {response.text}")
            
            return response.json()
    
    async def sync_user_profile(
        self,
        db: Session,
        user: User
    ) -> User:
        """Синхронизация профиля пользователя с HH.ru"""
        if not user.hh_access_token:
            raise ValueError("User has no HH access token")
        
        # Проверяем, не истек ли токен
        if user.hh_token_expires_at and user.hh_token_expires_at < datetime.utcnow():
            if user.hh_refresh_token:
                token_data = await self.refresh_access_token(user.hh_refresh_token)
                user.hh_access_token = token_data["access_token"]
                if "refresh_token" in token_data:
                    user.hh_refresh_token = token_data["refresh_token"]
                user.hh_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        
        # Получаем резюме
        if user.hh_resume_id:
            resume_data = await self.get_resume(user.hh_access_token, user.hh_resume_id)
            user = await self.import_resume_to_user(db, user, resume_data)
        else:
            # Если резюме не выбрано, берем первое доступное
            resumes = await self.get_resumes(user.hh_access_token)
            if resumes:
                resume_id = resumes[0]["id"]
                user.hh_resume_id = resume_id
                resume_data = await self.get_resume(user.hh_access_token, resume_id)
                user = await self.import_resume_to_user(db, user, resume_data)
        
        db.commit()
        db.refresh(user)
        
        return user


# Глобальный экземпляр сервиса
hh_integration = HHIntegration()
















