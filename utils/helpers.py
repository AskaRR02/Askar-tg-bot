import hashlib
import uuid
from typing import Dict, List, Union, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.models import User, Session, TestResult


async def get_or_create_user(session: AsyncSession, user_id: int, username: str = None) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        user = User(id=user_id, username=username)
        session.add(user)
        await session.commit()
        
    return user


async def get_or_create_session(session: AsyncSession, user_id: int) -> Session:
    result = await session.execute(select(Session).where(Session.user_id == user_id))
    user_session = result.scalars().first()
    
    if not user_session:
        user_session = Session(user_id=user_id)
        session.add(user_session)
        await session.commit()
        
    return user_session


async def update_session(session: AsyncSession, user_id: int, **kwargs) -> Session:
    result = await session.execute(select(Session).where(Session.user_id == user_id))
    user_session = result.scalars().first()
    
    if user_session:
        for key, value in kwargs.items():
            if hasattr(user_session, key):
                setattr(user_session, key, value)
        
        await session.commit()
        
    return user_session


async def save_test_result(session: AsyncSession, user_id: int, theme: str, score: float) -> TestResult:
    test_result = TestResult(user_id=user_id, theme=theme, score=score)
    session.add(test_result)
    await session.commit()
    return test_result


async def get_user_progress(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    result = await session.execute(select(TestResult).where(TestResult.user_id == user_id))
    test_results = result.scalars().all()
    
    themes = {}
    for result in test_results:
        if result.theme not in themes or result.score > themes[result.theme]:
            themes[result.theme] = result.score
    
    return {
        "completed_themes": list(themes.keys()),
        "scores": themes,
        "average_score": sum(themes.values()) / len(themes) if themes else 0
    }


def generate_phishing_link() -> str:
    unique_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
    return f"https://securit-y-check.com/{unique_id}"


def sanitize_filename(filename: str) -> str:
    return "".join(c for c in filename if c.isalnum() or c in "._- ").strip() 