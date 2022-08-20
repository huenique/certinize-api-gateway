# orjson raises E0611 and E1101
# pylint: disable=E1101

import typing
import uuid

import orjson
import pydantic
import sortedcontainers
import starlite
from sqlalchemy import exc

from app.db import crud
from app.models.domain import configuration
from app.models.schemas import configurations, fonts, templates


class ConfigurationService:
    async def create_template_config(
        self,
        data: configuration.TemplateConfiguration,
        certificate_config_schema: type[configurations.Configurations],
        database: crud.DatabaseImpl,
    ) -> dict[str, uuid.UUID | typing.Any]:
        font_id = data.font_id
        template_id = data.template_id
        config_meta = data.__dict__
        template_config_id = uuid.uuid1()

        # Reusing a variable seems more efficient and correct than extracting the value
        # from the dict everytime we need it.
        template_config_name = config_meta["template_config_name"]

        # SQLAlchemy rejects objects, so convert them to their string reprs.
        config_meta["template_id"] = str(config_meta["template_id"])
        config_meta["font_id"] = str(config_meta["font_id"])

        # Delete unsued fields
        del config_meta["font_id"]
        del config_meta["template_config_name"]
        del config_meta["template_id"]

        try:
            certificate_config = await database.select_row(
                table_model=certificate_config_schema(template_config_name=""),
                attribute="template_config_name",
                query=template_config_name,
            )

            return dict(
                sortedcontainers.SortedDict(
                    orjson.loads(certificate_config.one().json())
                )
            )
        except exc.NoResultFound:
            await database.add_row(
                certificate_config_schema(
                    template_config_id=template_config_id,
                    config_meta=config_meta,
                    template_config_name=template_config_name,
                    font_id=font_id,
                    template_id=template_id,
                )
            )

            return dict(
                sortedcontainers.SortedDict(
                    {
                        "template_config_id": template_config_id,
                        "template_config_name": template_config_name,
                        "config_meta": {
                            "recipient_name": config_meta["recipient_name"],
                            "issuance_date": config_meta["issuance_date"],
                        },
                        "template_id": font_id,
                        "font_id": template_id,
                    }
                )
            )

    async def get_template_config(  # pylint: disable=R0913
        self,
        template_config_id: pydantic.UUID1,
        certificate_config_schema: type[configurations.Configurations],
        templates_schema: type[templates.Templates],
        fonts_schema: type[fonts.Fonts],
        database: crud.DatabaseImpl,
    ):
        try:
            certificate_config = await database.select_join(
                certificate_config_schema(
                    template_config_id=template_config_id, template_config_name=""
                ),
                certificate_config_schema,
                templates_schema,
                fonts_schema,
            )
            return certificate_config.one()
        except exc.NoResultFound as err:
            raise starlite.NotFoundException(str(err)) from err

    async def list_template_config(
        self,
        certificate_config_schema: type[configurations.Configurations],
        templates_schema: type[templates.Templates],
        fonts_schema: type[fonts.Fonts],
        database: crud.DatabaseImpl,
    ):
        result = await database.select_all_join(
            *(certificate_config_schema, templates_schema, fonts_schema),
        )

        serialized_results: list[dict[str, dict[str, typing.Any]]] = []
        for result in result.all():
            # In case this becomes confusing, here's what happens here:
            # 1. Convert the Row to its JSON representation.
            # 2. Deserialize the JSON repr using orjson.loads().
            # 3. Use SortedDict to sort the contents of the dict.
            # 4. Convert the SortedDict object to dict using dict().
            # 5. Assign the result to a parent dict key.
            # 6. Append the parent dict to serialized_results.
            serialized_results.append(
                {
                    "template_config": dict(
                        sortedcontainers.SortedDict(
                            orjson.loads(result["Configurations"].json())
                        )
                    ),
                    "template": dict(
                        sortedcontainers.SortedDict(
                            orjson.loads(result["Templates"].json())
                        )
                    ),
                    "font": dict(
                        sortedcontainers.SortedDict(
                            orjson.loads(result["Fonts"].json())
                        )
                    ),
                }
            )

        return {"configurations": serialized_results}
