from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Tuple
import random

from ..models.pet import PetConfig, CharacterPet
from ..models.character import Character
from ..game.formulas import calc_pet_combat_stats
from ..utils.id_gen import generate_id
from ..exceptions import PetException, ValidationException


class PetService:
    @staticmethod
    async def get_pet_config(db: AsyncSession, pet_config_id: int) -> Optional[PetConfig]:
        result = await db.execute(select(PetConfig).where(PetConfig.id == pet_config_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_char_pets(db: AsyncSession, char: Character) -> List[CharacterPet]:
        result = await db.execute(
            select(CharacterPet).where(CharacterPet.character_id == char.id).order_by(CharacterPet.slot_index)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_pet_with_config(db: AsyncSession, pet_id: int, char: Character) -> Optional[Tuple[CharacterPet, PetConfig]]:
        result = await db.execute(
            select(CharacterPet, PetConfig)
            .join(PetConfig, CharacterPet.pet_config_id == PetConfig.id)
            .where(and_(CharacterPet.id == pet_id, CharacterPet.character_id == char.id))
        )
        return result.first()

    @staticmethod
    async def set_battle_pet(db: AsyncSession, char: Character, pet_id: int):
        result = await db.execute(
            select(CharacterPet).where(
                and_(CharacterPet.id == pet_id, CharacterPet.character_id == char.id)
            )
        )
        pet = result.scalar_one_or_none()
        if not pet:
            raise PetException("宠物不存在")
        await db.execute(
            __import__("sqlalchemy").update(CharacterPet)
            .where(and_(CharacterPet.character_id == char.id, CharacterPet.is_battle == True))
            .values(is_battle=False)
        )
        pet.is_battle = True
        await db.flush()

    @staticmethod
    async def add_pet_capture(db: AsyncSession, char: Character, pet_config_id: int) -> CharacterPet:
        cfg = await PetService.get_pet_config(db, pet_config_id)
        if not cfg:
            raise PetException("宠物种类不存在")
        pets = await PetService.get_char_pets(db, char)
        if len(pets) >= 8:
            raise PetException("宠物栏已满")
        battle_slot = None
        all_slots = set(p.slot_index for p in pets)
        for i in range(8):
            if i not in all_slots:
                battle_slot = i
                break
        variance = 0.05
        gz = int(cfg.base_attack * random.uniform(1 - variance, 1 + variance))
        fy = int(cfg.base_defense * random.uniform(1 - variance, 1 + variance))
        tz = int(cfg.base_hp * random.uniform(1 - variance, 1 + variance))
        fz = int(cfg.base_magic * random.uniform(1 - variance, 1 + variance))
        sd = int(cfg.base_speed * random.uniform(1 - variance, 1 + variance))
        growth = round(float(cfg.growth_rate) * random.uniform(0.95, 1.05), 3)
        combat = calc_pet_combat_stats(1, gz, fy, tz, sd, fz, growth)
        pet = CharacterPet(
            id=generate_id(),
            character_id=char.id,
            pet_config_id=cfg.id,
            nickname=cfg.name,
            level=1,
            exp=0,
            hp=combat["hp_max"],
            mp=combat["mp_max"],
            loyalty=100,
            life=10000,
            is_battle=all(not p.is_battle for p in pets),
            slot_index=battle_slot,
            skills=list(cfg.possible_skills)[:2] if isinstance(cfg.possible_skills, list) else [],
            attr_gz=gz,
            attr_fy=fy,
            attr_tz=tz,
            attr_fz=fz,
            attr_sd=sd,
            growth=growth,
        )
        db.add(pet)
        await db.flush()
        return pet

    @staticmethod
    async def release_pet(db: AsyncSession, char: Character, pet_id: int):
        result = await db.execute(
            select(CharacterPet).where(
                and_(CharacterPet.id == pet_id, CharacterPet.character_id == char.id)
            )
        )
        pet = result.scalar_one_or_none()
        if not pet:
            raise PetException("宠物不存在")
        if pet.is_battle:
            raise PetException("出战宠物不能放生，请先切换")
        await db.delete(pet)

    @staticmethod
    async def get_battle_pet(db: AsyncSession, char: Character) -> Optional[Tuple[CharacterPet, PetConfig]]:
        result = await db.execute(
            select(CharacterPet, PetConfig)
            .join(PetConfig, CharacterPet.pet_config_id == PetConfig.id)
            .where(and_(CharacterPet.character_id == char.id, CharacterPet.is_battle == True))
        )
        return result.first()


pet_service = PetService()
