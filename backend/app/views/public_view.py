from marshmallow import Schema, fields, validate


class PublicWhatsAppItemSchema(Schema):
    product_id = fields.UUID(required=True)
    quantity = fields.Integer(required=True, validate=validate.Range(min=1, max=999))


class PublicWhatsAppSchema(Schema):
    fair_id = fields.UUID(load_default=None)
    items = fields.List(
        fields.Nested(PublicWhatsAppItemSchema),
        required=True,
        validate=validate.Length(min=1, max=50),
    )
