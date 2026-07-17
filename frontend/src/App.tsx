import { Routes, Route, Link, Navigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { CalendarDays, MessageCircle, MapPin, Store } from "lucide-react";
import { api, Exhibitor, Fair, Product } from "./api";
import { useState } from "react";
import { LoginPage, ChangePasswordPage, DashboardPage } from "./AuthPages";
import {
  AdminDashboard,
  AdministratorsPage,
  ExhibitorsPage,
  FairsPage,
  CategoriesPage,
  AuditPage,
  ProductsPage,
} from "./AdminPortal";

const date = (v: string) =>
  new Intl.DateTimeFormat("es-BO", { timeZone: "America/La_Paz" }).format(
    new Date(v + "T12:00:00"),
  );
const money = (v: number | null) => (v === null ? "" : `Bs. ${v.toFixed(2)}`);

function Header() {
  return (
    <header className="bg-primary text-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between p-5">
        <Link to="/catalogo" className="text-xl font-bold">
          Catálogo Digital de Ferias
        </Link>
        <Link
          to="/gestion/login"
          className="rounded-lg border border-surface px-4 py-2"
        >
          Iniciar Sesión
        </Link>
      </div>
    </header>
  );
}

function Catalog() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["active-fair"],
    queryFn: () =>
      api
        .get<Fair & { expositores: Exhibitor[] }>("/public/active-fair")
        .then((r) => r.data),
  });
  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl p-6">
        {isLoading ? (
          <p>Cargando feria activa...</p>
        ) : error ? (
          <section className="bg-active rounded-xl p-6">
            <h1 className="text-2xl font-bold">No existe una feria activa</h1>
            <p className="mt-2">
              El catálogo público estará disponible cuando exista una Feria
              disponible.
            </p>
          </section>
        ) : (
          data && (
            <>
              <div className="mb-8 overflow-hidden rounded-2xl bg-primary text-surface">
                <img
                  className="h-64 w-full object-cover opacity-80"
                  src={data.imagen_portada}
                  alt=""
                />
                <div className="p-6">
                  <p className="mb-2 font-semibold text-accent">Feria activa</p>
                  <h1 className="text-4xl font-bold">{data.nombre}</h1>
                  <p className="mt-3 max-w-3xl">{data.descripcion}</p>
                  <p className="mt-4 flex flex-wrap gap-4 text-sm">
                    <span className="flex items-center gap-2">
                      <MapPin size={18} />
                      {data.lugar}, {data.municipio}
                    </span>
                    <span className="flex items-center gap-2">
                      <CalendarDays size={18} />
                      {date(data.fecha_inicio)} - {date(data.fecha_fin)}
                    </span>
                  </p>
                </div>
              </div>
              <h2 className="text-2xl font-bold">Expositores autorizados</h2>
              <div className="mt-5 grid gap-5 md:grid-cols-3">
                {data.expositores?.length ? (
                  data.expositores.map((e) => (
                    <motion.article
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="card"
                      key={e.id}
                    >
                      {e.logo && (
                        <img
                          className="mb-4 h-32 w-full rounded-xl object-cover"
                          src={e.logo}
                          alt=""
                        />
                      )}
                      <Store className="text-primary" />
                      <h3 className="mt-3 text-xl font-bold">
                        {e.nombre_comercial}
                      </h3>
                      <p className="mt-2 text-muted">{e.descripcion}</p>
                      <Link
                        className="btn mt-5 w-full"
                        to={`/catalogo/expositores/${e.id}`}
                      >
                        Ver productos
                      </Link>
                    </motion.article>
                  ))
                ) : (
                  <p className="rounded-xl bg-active p-5">
                    Todavía no hay expositores autorizados para esta feria.
                  </p>
                )}
              </div>
            </>
          )
        )}
      </main>
    </>
  );
}

function ExhibitorPage() {
  const { expositorId } = useParams();
  const { data: fair } = useQuery({
    queryKey: ["active-fair"],
    queryFn: () => api.get<Fair>("/public/active-fair").then((r) => r.data),
  });
  const { data, isLoading } = useQuery({
    queryKey: ["active-exhibitor", fair?.slug, expositorId],
    enabled: !!fair?.slug && !!expositorId,
    queryFn: () =>
      api
        .get(`/public/fairs/${fair!.slug}/exhibitors/${expositorId}`)
        .then((r) => r.data),
  });
  const [selected, setSelected] = useState<Product[]>([]);
  const toggle = (p: Product) =>
    setSelected((s) =>
      s.some((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : [...s, p],
    );
  const consult = async () => {
    const r = await api.post("/public/whatsapp-query", {
      fair_slug: fair?.slug,
      product_ids: selected.map((p) => p.id),
    });
    window.open(r.data.url, "_blank", "noopener,noreferrer");
  };
  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl p-6">
        <Link to="/catalogo" className="text-primary">
          ← Volver al catálogo
        </Link>
        {isLoading ? (
          <p className="mt-6">Cargando productos...</p>
        ) : (
          data && (
            <>
              <h1 className="mt-5 text-4xl font-bold">
                {data.nombre_comercial}
              </h1>
              <p className="mt-2 text-muted">{data.descripcion}</p>
              <div className="mt-8 grid gap-5 md:grid-cols-3">
                {data.productos.map((p: Product) => {
                  const available = p.estado === "AVAILABLE";
                  return (
                    <article className="card" key={p.id}>
                      {p.imagenes[0] && (
                        <img
                          className="mb-4 h-44 w-full rounded-xl object-cover"
                          src={p.imagenes[0].url}
                        />
                      )}
                      <h2 className="text-xl font-bold">{p.nombre}</h2>
                      <p className="mt-2 text-muted">{p.descripcion}</p>
                      {p.precio !== null && (
                        <p className="mt-3 font-semibold text-price">
                          {money(p.precio)}
                        </p>
                      )}
                      <button
                        disabled={!available}
                        onClick={() => toggle(p)}
                        className={`mt-4 w-full rounded-xl border p-3 font-semibold ${selected.some((x) => x.id === p.id) ? "bg-primary text-surface" : "border-primary text-primary"}`}
                      >
                        {available
                          ? selected.some((x) => x.id === p.id)
                            ? "Seleccionado"
                            : "Seleccionar"
                          : "No disponible"}
                      </button>
                    </article>
                  );
                })}
              </div>
            </>
          )
        )}
        {selected.length > 0 && (
          <div className="fixed bottom-5 left-1/2 flex -translate-x-1/2 items-center gap-4 rounded-2xl bg-surface p-4 shadow-2xl">
            <span>{selected.length} seleccionado(s)</span>
            <button
              className="btn-secondary gap-2 rounded-xl px-5 py-3 font-semibold"
              onClick={consult}
            >
              <MessageCircle />
              Consultar por WhatsApp
            </button>
          </div>
        )}
      </main>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/catalogo" replace />} />
      <Route path="/catalogo" element={<Catalog />} />
      <Route
        path="/catalogo/expositores/:expositorId"
        element={<ExhibitorPage />}
      />
      <Route
        path="/catalogo/ferias/:slug"
        element={<Navigate to="/catalogo" replace />}
      />
      <Route path="/gestion/login" element={<LoginPage />} />
      <Route
        path="/gestion/cambiar-contrasena"
        element={<ChangePasswordPage />}
      />
      <Route path="/gestion/admin/dashboard" element={<AdminDashboard />} />
      <Route
        path="/gestion/admin/administradores"
        element={<AdministratorsPage />}
      />
      <Route path="/gestion/admin/expositores" element={<ExhibitorsPage />} />
      <Route path="/gestion/admin/ferias" element={<FairsPage />} />
      <Route path="/gestion/admin/categorias" element={<CategoriesPage />} />
      <Route
        path="/gestion/admin/productos"
        element={<ProductsPage mode="admin" />}
      />
      <Route path="/gestion/admin/auditoria" element={<AuditPage />} />
      <Route
        path="/gestion/expositor/dashboard"
        element={<ProductsPage mode="expositor" />}
      />
      <Route path="*" element={<Navigate to="/catalogo" />} />
    </Routes>
  );
}
