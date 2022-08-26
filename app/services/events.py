"""
app.services.events
~~~~~~~~~~~~~~~~~~~

This module contains functions that the ASGI server will invoke on on_startup &
on_shutdown events.
"""
import aiohttp
import starlite

from app.core.config import settings
from app.services import image_processor


async def create_image_processor_client(state: starlite.State) -> None:
    state.image_processor = image_processor.ImageProcessor(
        settings.certinize_image_processor
    )
    state.image_processor_session = state.image_processor.session


async def dispose_client_sessions(state: starlite.State) -> None:
    if isinstance(state.image_processor_session, aiohttp.ClientSession):
        await state.image_processor_session.close()
