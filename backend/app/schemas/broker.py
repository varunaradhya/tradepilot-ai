from datetime import datetime

from pydantic import BaseModel, Field


class BrokerConnectRequest(BaseModel):

    broker_name: str = Field(
        min_length=1,
        max_length=50,
    )

    client_id: str = Field(
        min_length=1,
        max_length=100,
    )

    access_token: str = Field(
        min_length=10,
    )

    token_expires_at: datetime | None = None


class BrokerConnectionResponse(BaseModel):

    id: int
    broker_name: str
    client_id: str
    status: str
    token_expires_at: datetime | None
    last_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_message: str | None

    model_config = {
        "from_attributes": True,
    }


class BrokerSyncResponse(BaseModel):

    broker_name: str
    status: str
    holdings_imported: int
    transactions_imported: int
    holdings_updated: int
    message: str
    synced_at: datetime
