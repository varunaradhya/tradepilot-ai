from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.broker_security import (
    decrypt_secret,
    encrypt_secret,
)
from app.models.broker_connection import BrokerConnection


def save_broker_connection(
    db: Session,
    user_id: int,
    broker_name: str,
    client_id: str,
    access_token: str,
    token_expires_at=None,
):
    broker_name = broker_name.strip().upper()
    query = db.query(BrokerConnection).filter(
        BrokerConnection.user_id == user_id,
        BrokerConnection.broker_name == broker_name,
    )
    connection = query.with_for_update().first()
    encrypted = encrypt_secret(access_token)

    if connection is None:
        try:
            connection = BrokerConnection(
                user_id=user_id,
                broker_name=broker_name,
                client_id=client_id,
                encrypted_access_token=encrypted,
                token_expires_at=token_expires_at,
                status="CONNECTED",
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)
            return connection
        except IntegrityError:
            db.rollback()
            connection = query.with_for_update().one()

    connection.client_id = client_id
    connection.encrypted_access_token = encrypted
    connection.token_expires_at = token_expires_at
    connection.status = "CONNECTED"
    db.commit()
    db.refresh(connection)
    return connection


def get_user_broker(
    db: Session,
    user_id: int,
    broker_name: str,
):
    return (
        db.query(BrokerConnection)
        .filter(
            BrokerConnection.user_id == user_id,
            BrokerConnection.broker_name == broker_name.strip().upper(),
        )
        .first()
    )


def get_access_token(connection: BrokerConnection):
    return decrypt_secret(connection.encrypted_access_token)


def mark_sync_result(
    db: Session,
    connection: BrokerConnection,
    success: bool,
    message: str,
):
    connection = (
        db.query(BrokerConnection)
        .filter(
            BrokerConnection.id == connection.id,
            BrokerConnection.user_id == connection.user_id,
        )
        .with_for_update()
        .one()
    )
    connection.last_sync_at = datetime.now(timezone.utc)
    connection.last_sync_status = "SUCCESS" if success else "FAILED"
    # Persist only controlled status text. Broker/API exception messages may
    # contain request details that should not become durable connection metadata.
    connection.last_sync_message = (
        "Dhan portfolio synchronized."
        if success
        else "Dhan portfolio synchronization failed."
    )
    if not success:
        connection.status = "ERROR"
    db.commit()
    db.refresh(connection)
