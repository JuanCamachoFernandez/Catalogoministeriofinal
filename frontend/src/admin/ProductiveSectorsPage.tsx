import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { api, type Paged, type ProductiveSector } from "../api";
import {
  Empty,
  Field,
  Loading,
  Modal,
  PaginationBar,
  StatusBadge,
  useFeedback,
} from "../ui";
import { clean, message, pageData } from "./adminShared";

export default function ProductiveSectorsPage() {
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<ProductiveSector | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [other, setOther] = useState(false);

  const qc = useQueryClient();
  const feedback = useFeedback();

  const list = useQuery({
    queryKey: ["productive-sectors", "admin", page],
    queryFn: () =>
      api
        .get<Paged<ProductiveSector>>("/admin/productive-sectors", {
          params: { per_page: 10, page },
        })
        .then((response) => response.data),
  });

  const open = (item?: ProductiveSector) => {
    setEditing(item ?? null);
    setCreating(!item);
    setName(item?.nombre ?? "");
    setDescription(item?.descripcion ?? "");
    setOther(item?.es_otro ?? false);
  };

  const save = async () => {
    try {
      if (editing) {
        await api.patch(`/admin/productive-sectors/${editing.id}`, {
          nombre: name,
          descripcion: clean(description),
          es_otro: other,
        });
      } else {
        await api.post("/admin/productive-sectors", {
          nombre: name,
          descripcion: clean(description),
          es_otro: other,
        });
      }

      await qc.invalidateQueries({ queryKey: ["productive-sectors"] });
      setEditing(null);
      setCreating(false);
      feedback.success("Sector guardado", name);
    } catch (error) {
      feedback.error("No se pudo guardar", message(error));
    }
  };

  const data = pageData(list.data);
  const items = data.items;

  return (
    <section className="admin-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Clasificación institucional</span>
          <h1>Sectores Productivos</h1>
        </div>
        <button className="admin-units-create-button" onClick={() => open()}>
          <Plus aria-hidden="true" />
          Nuevo sector
        </button>
      </div>

      {list.isLoading ? (
        <Loading />
      ) : list.error ? (
        <Empty
          title="No se pudieron cargar los sectores"
          description={message(list.error)}
        />
      ) : items.length ? (
        <>
          <div className="table-wrap admin-requests-table admin-units-table">
            <table>
              <thead>
                <tr>
                  <th>Sector</th>
                  <th>Descripción</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.nombre}</td>
                    <td>
                      <span
                        className="admin-sector-description-cell"
                        title={item.descripcion || ""}
                      >
                        {item.descripcion || "Sin descripción"}
                      </span>
                    </td>
                    <td>
                      <StatusBadge value={item.estado} />
                    </td>
                    <td>
                      <button
                        className="btn-small admin-sector-action-button admin-sector-action-edit"
                        onClick={() => open(item)}
                      >
                        Editar
                      </button>{" "}
                      <button
                        className={`btn-small admin-sector-action-button ${
                          item.estado === "ACTIVE"
                            ? "admin-sector-action-disable"
                            : "admin-sector-action-enable"
                        }`}
                        onClick={async () => {
                          await api.patch(
                            `/admin/productive-sectors/${item.id}/status`,
                            {
                              estado:
                                item.estado === "ACTIVE" ? "INACTIVE" : "ACTIVE",
                            },
                          );
                          await qc.invalidateQueries({
                            queryKey: ["productive-sectors"],
                          });
                        }}
                      >
                        {item.estado === "ACTIVE" ? "Deshabilitar" : "Activar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PaginationBar pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <Empty title="No hay Sectores Productivos" />
      )}

      {(editing || creating) && (
        <Modal
          title={editing ? "Editar sector" : "Nuevo sector"}
          className="admin-sector-modal"
          onClose={() => {
            setEditing(null);
            setCreating(false);
          }}
        >
          <div className="admin-sector-modal-content">
            <p className="admin-sector-modal-intro">
              Define el nombre, la descripción y la clasificación operativa del sector.
            </p>
            <Field label="Nombre">
              <input
                className="input"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
            <Field label="Descripción">
              <textarea
                className="input"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </Field>
            <label className="admin-sector-modal-check">
              <input
                type="checkbox"
                checked={other}
                onChange={(event) => setOther(event.target.checked)}
              />
              <span>Marcar como sector “Otros”</span>
            </label>
            <div className="modal-actions admin-sector-modal-actions">
              <button
                className="admin-unit-action-button"
                disabled={!name.trim()}
                onClick={() => void save()}
              >
                Guardar
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
