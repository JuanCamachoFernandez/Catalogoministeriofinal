import { useEffect, useMemo, useState } from "react";
import { assetUrl, type CanonicalProduct, type Pagination } from "../api";
import { Empty, PaginationBar, SearchField, StatusBadge } from "../ui";

const PRODUCTS_PER_PAGE = 5;

export function ProductiveUnitProductsSection({
  products,
  onSelectProduct,
}: {
  products: CanonicalProduct[];
  onSelectProduct: (product: CanonicalProduct) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filteredProducts = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("es");
    if (!normalized) return products;
    return products.filter((product) =>
      product.nombre_comercial.toLocaleLowerCase("es").includes(normalized),
    );
  }, [products, query]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredProducts.length / PRODUCTS_PER_PAGE),
  );
  const safePage = Math.min(page, totalPages);
  const startIndex = (safePage - 1) * PRODUCTS_PER_PAGE;
  const visibleProducts = filteredProducts.slice(
    startIndex,
    startIndex + PRODUCTS_PER_PAGE,
  );

  useEffect(() => {
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pagination: Pagination = {
    page: safePage,
    per_page: PRODUCTS_PER_PAGE,
    pages: totalPages,
    total: filteredProducts.length,
    has_prev: safePage > 1,
    has_next: safePage < totalPages,
  };

  return (
    <section className="admin-unit-detail-section">
      <div className="admin-unit-detail-section-heading">
        <div>
          <h3>Productos</h3>
          <p>{products.length} registrados</p>
        </div>
      </div>

      {products.length ? (
        <>
          <div className="admin-unit-products-toolbar">
            <SearchField
              value={query}
              onChange={setQuery}
              placeholder="Buscar producto..."
            />
          </div>

          {visibleProducts.length ? (
            <div className="table-wrap admin-requests-table admin-unit-products-table">
              <table>
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>Precio</th>
                    <th>Estado</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {visibleProducts.map((product) => {
                    const cover =
                      product.imagenes.find((image) => image.es_principal) ??
                      product.imagenes[0] ??
                      null;
                    return (
                      <tr key={product.id}>
                        <td>
                          <div className="admin-unit-product-cell">
                            <div className="admin-unit-product-cell-media">
                              {cover ? (
                                <img
                                  src={assetUrl(cover.url_imagen)}
                                  alt={product.nombre_comercial}
                                />
                              ) : (
                                <div className="admin-unit-product-cell-fallback">
                                  Sin imagen
                                </div>
                              )}
                            </div>
                            <div className="admin-unit-product-cell-copy">
                              <strong>{product.nombre_comercial}</strong>
                            </div>
                          </div>
                        </td>
                        <td>Bs {Number(product.precio_referencia).toFixed(2)}</td>
                        <td>
                          <StatusBadge value={product.estado} />
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn-small"
                            onClick={() => onSelectProduct(product)}
                          >
                            Ver
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="No se encontraron productos"
              description="Pruebe con otro nombre."
            />
          )}

          <PaginationBar pagination={pagination} onPageChange={setPage} />
        </>
      ) : (
        <Empty title="Sin productos" />
      )}
    </section>
  );
}
