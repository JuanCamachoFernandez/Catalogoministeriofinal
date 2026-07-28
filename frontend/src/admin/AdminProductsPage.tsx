import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  api,
  assetUrl,
  type CanonicalProduct,
  type Paged,
  type ProductiveUnit,
} from "../api";
import {
  Empty,
  ErrorBox,
  Loading,
  PaginationBar,
  SearchField,
  SearchableSelect,
  StatusBadge,
  useFeedback,
} from "../ui";
import { message, pageData } from "./adminShared";

const PRODUCT_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "DRAFT", label: "En preparación" },
  { value: "AVAILABLE", label: "Disponible" },
  { value: "RETIRED", label: "Retirado" },
];

const PRODUCT_EDITABLE_STATES = [
  { value: "DRAFT", label: "En preparación" },
  { value: "AVAILABLE", label: "Disponible" },
  { value: "RETIRED", label: "Retirado" },
];

export default function AdminProductsPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [productiveUnitId, setProductiveUnitId] = useState("");

  const productiveUnits = useQuery({
    queryKey: ["admin-products-productive-units"],
    queryFn: () =>
      api
        .get<Paged<ProductiveUnit>>("/admin/productive-units", {
          params: { include_deleted: true, per_page: 200 },
        })
        .then((response) => response.data.items),
  });

  const list = useQuery({
    queryKey: ["admin-products", page, q, status, productiveUnitId],
    queryFn: () =>
      api
        .get<Paged<CanonicalProduct>>("/admin/products", {
          params: {
            page,
            q: q || undefined,
            estado: status || undefined,
            productive_unit_id: productiveUnitId || undefined,
          },
        })
        .then((response) => response.data),
  });

  const qc = useQueryClient();
  const feedback = useFeedback();
  const data = pageData(list.data);

  return (
    <section className="admin-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Oferta productiva</span>
          <h1>Productos registrados</h1>
        </div>
      </div>

      <div className="toolbar admin-units-toolbar">
        <SearchField
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar producto..."
        />
        <SearchableSelect
          value={productiveUnitId}
          options={[
            { value: "", label: "Todas las unidades" },
            ...(productiveUnits.data?.map((unit) => ({
              value: unit.id,
              label: unit.nombre_comercial,
            })) ?? []),
          ]}
          onChange={(value) => {
            setProductiveUnitId(value);
            setPage(1);
          }}
          placeholder="Todas las unidades"
          searchPlaceholder="Buscar unidad productiva..."
          ariaLabel="Filtrar por unidad productiva"
        />
        <SearchableSelect
          value={status}
          options={PRODUCT_STATUS_OPTIONS}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          placeholder="Todos los estados"
          searchPlaceholder="Buscar estado..."
          ariaLabel="Filtrar por estado"
        />
      </div>

      {list.isLoading ? (
        <Loading />
      ) : list.error ? (
        <ErrorBox message={message(list.error)} />
      ) : data.items.length ? (
        <>
          <div className="table-wrap admin-requests-table admin-units-table">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Unidad Productiva</th>
                  <th>Precio</th>
                  <th>Imágenes</th>
                  <th>Estado</th>
                  <th>Actualizar</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((product) => {
                  const unit = productiveUnits.data?.find(
                    (item) => item.id === product.productive_unit_id,
                  );
                  const primaryImage =
                    product.imagenes.find((image) => image.es_principal) ??
                    product.imagenes[0];
                  const stateOptions = PRODUCT_EDITABLE_STATES.some(
                    (option) => option.value === product.estado,
                  )
                    ? PRODUCT_EDITABLE_STATES
                    : [
                        ...PRODUCT_EDITABLE_STATES,
                        {
                          value: product.estado,
                          label:
                            product.estado === "OUT_OF_STOCK"
                              ? "Sin stock (legado)"
                              : product.estado,
                        },
                      ];
                  return (
                    <tr key={product.id}>
                      <td>
                        <div className="admin-products-product-cell">
                          <div className="admin-products-product-thumb">
                            {primaryImage ? (
                              <img
                                src={assetUrl(primaryImage.url_imagen)}
                                alt={product.nombre_comercial}
                              />
                            ) : (
                              <span>Sin imagen</span>
                            )}
                          </div>
                          <div className="admin-products-product-meta">
                            <strong>{product.nombre_comercial}</strong>
                          </div>
                        </div>
                      </td>
                      <td>
                        <strong>
                          {unit?.nombre_comercial ?? "Unidad no encontrada"}
                        </strong>
                      </td>
                      <td>Bs {Number(product.precio_referencia).toFixed(2)}</td>
                      <td>{product.imagenes.length}/3</td>
                      <td>
                        <StatusBadge
                          value={
                            product.estado === "OUT_OF_STOCK"
                              ? "DRAFT"
                              : product.estado
                          }
                        />
                      </td>
                      <td>
                        <SearchableSelect
                          className="admin-products-state-filter"
                          value={product.estado}
                          options={stateOptions}
                          searchable={false}
                          placeholder="Actualizar estado"
                          ariaLabel={`Actualizar estado de ${product.nombre_comercial}`}
                          onChange={async (value) => {
                            try {
                              await api.patch(
                                `/admin/products/${product.id}/status`,
                                { estado: value },
                              );
                              await qc.invalidateQueries({
                                queryKey: ["admin-products"],
                              });
                              feedback.success(
                                "Estado actualizado",
                                product.nombre_comercial,
                              );
                            } catch (error) {
                              feedback.error(
                                "No se pudo actualizar el estado",
                                message(error),
                              );
                            }
                          }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <PaginationBar pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <Empty title="No hay productos" />
      )}
    </section>
  );
}
