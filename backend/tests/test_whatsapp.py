from datetime import timedelta
from urllib.parse import unquote
from app.extensiones import db
from app.modelos import (
    AssignmentStatus, Category, DocumentType, Exhibitor, Fair,
    FairExhibitor, FeriaStatus, Product, ProductStatus, Role, User, UserStatus,
    bolivia_today,
)


def setup_catalog():
    admin=User(username="admin",email="admin@gmail.com",password_hash="hash",role=Role.SUPERADMIN,first_name="A",last_name="B",status=UserStatus.ACTIVE,must_change_password=False)
    owner=User(username="expositor",email="expositor@gmail.com",password_hash="hash",role=Role.EXPOSITOR,first_name="E",last_name="X",status=UserStatus.ACTIVE,must_change_password=False)
    db.session.add_all([admin,owner]);db.session.flush()
    exhibitor=Exhibitor(user_id=owner.id,nombre_comercial="Artesanías Bolivia",tipo_documento=DocumentType.CI,numero_documento="123",nombre_responsable="E",apellido_responsable="X",telefono_whatsapp="59171234567",correo="expositor@gmail.com",departamento="La Paz",municipio="La Paz",estado=UserStatus.ACTIVE)
    category=Category(nombre="Artesanía",slug="artesania",estado=True)
    today=bolivia_today()
    fair=Fair(nombre="Feria Test",slug="feria-test",lugar="Plaza",departamento="La Paz",fecha_inicio=today,fecha_fin=today+timedelta(days=1),imagen_portada=None,estado=FeriaStatus.PUBLISHED,visible_publicamente=True,created_by=admin.id)
    db.session.add_all([exhibitor,category,fair]);db.session.flush()
    assignment=FairExhibitor(fair_id=fair.id,exhibitor_id=exhibitor.id,estado=AssignmentStatus.AUTHORIZED)
    product=Product(exhibitor_id=exhibitor.id,category_id=category.id,nombre="Producto propio",slug="producto-propio",descripcion="Descripción",estado=ProductStatus.AVAILABLE)
    db.session.add_all([assignment,product]);db.session.commit()
    return product


def test_consulta_usa_whatsapp_del_propietario(app,client):
    with app.app_context(): product=setup_catalog();product_id=str(product.id)
    response=client.post("/api/public/whatsapp-query",json={"fair_slug":"feria-test","product_ids":[product_id]})
    assert response.status_code==200
    assert response.json["url"].startswith("https://wa.me/59171234567?text=")


def test_consulta_rechaza_producto_inexistente(client):
    response=client.post("/api/public/whatsapp-query",json={"fair_slug":"feria-test","product_ids":["00000000-0000-0000-0000-000000000001"]})
    assert response.status_code==400


def test_consulta_lista_productos_con_cantidad_y_rechaza_cero(app, client):
    with app.app_context():
        product = setup_catalog()
        product_id = str(product.id)
    response = client.post(
        "/api/public/whatsapp-query",
        json={
            "fair_slug": "feria-test",
            "items": [{"product_id": product_id, "quantity": 3}],
        },
    )
    assert response.status_code == 200
    message = unquote(response.json["url"])
    assert "• Producto propio — Cantidad: 3" in message
    assert "más información" in message
    assert "Expositor:" not in message

    invalid = client.post(
        "/api/public/whatsapp-query",
        json={
            "fair_slug": "feria-test",
            "items": [{"product_id": product_id, "quantity": 0}],
        },
    )
    assert invalid.status_code == 400
