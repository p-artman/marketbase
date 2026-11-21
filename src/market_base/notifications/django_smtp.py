"""Django email backend adapter (SMTP / console / any EMAIL_BACKEND)."""

from __future__ import annotations

import logging

from market_base.notifications.protocol import OrderEmailPayload

logger = logging.getLogger(__name__)


class DjangoEmailNotifier:
    """Uses django.core.mail — configure EMAIL_* in Django settings."""

    def send_order_confirmation(self, payload: OrderEmailPayload) -> None:
        subject = f'Заказ #{payload.order_id} принят'
        body = (
            f'Здравствуйте, {payload.customer_name}!\n\n'
            f'Ваш заказ #{payload.order_id} оформлен.\n'
            f'Сумма: {payload.total_amount} {payload.currency}\n'
            f'Статус оплаты: {payload.payment_status}\n'
            f'Адрес: {payload.shipping_address}\n'
            f'{payload.items_summary}\n\n'
            f'Спасибо за покупку!'
        )
        self._send(payload.to_email, subject, body)

    def send_payment_receipt(
        self,
        payload: OrderEmailPayload,
        *,
        payment_id: str = '',
    ) -> None:
        subject = f'Оплата заказа #{payload.order_id} получена'
        body = (
            f'Здравствуйте, {payload.customer_name}!\n\n'
            f'Оплата по заказу #{payload.order_id} прошла успешно.\n'
            f'Сумма: {payload.total_amount} {payload.currency}\n'
            f'ID платежа: {payment_id}\n'
            f'Адрес доставки: {payload.shipping_address}\n'
        )
        if payload.tracking_number:
            body += f'Трек-номер: {payload.tracking_number}\n'
        body += '\nФискальный чек (если требуется) также формирует YooKassa на указанный email.\n'
        self._send(payload.to_email, subject, body)

    @staticmethod
    def _send(to_email: str, subject: str, body: str) -> None:
        from django.conf import settings
        from django.core.mail import send_mail

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@market.local')
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info('Email sent to %s: %s', to_email, subject)
