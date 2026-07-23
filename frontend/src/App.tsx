import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ProtectedRoute } from "./AuthContext";
import { ManagementLayout } from "./Layouts";
import { Loading } from "./ui";

const pages = () => import("./CanonicalPages");
const pick = <T extends Record<string, unknown>, K extends keyof T>(loader:()=>Promise<T>,key:K)=>lazy(()=>loader().then(module=>({default:module[key] as React.ComponentType})));
const RegistrationPage=pick(pages,"RegistrationPage"),RegistrationRequestsPage=pick(pages,"RegistrationRequestsPage"),ProductiveUnitsPage=pick(pages,"ProductiveUnitsPage"),ProductiveSectorsPage=pick(pages,"ProductiveSectorsPage"),ProductsPage=pick(pages,"ProductsPage"),AdminProductsPage=pick(pages,"AdminProductsPage"),ProductiveUnitProfilePage=pick(pages,"ProductiveUnitProfilePage"),UnitSectorsPage=pick(pages,"UnitSectorsPage"),FairsPage=pick(pages,"FairsPage"),NotFoundPage=pick(pages,"NotFoundPage");
const PublicCatalogPage=pick(()=>import("./PublicCatalogPages"),"PublicCatalogPage"),PublicFairPage=pick(()=>import("./PublicCatalogPages"),"PublicFairPage"),PublicUnitPage=pick(()=>import("./PublicCatalogPages"),"PublicUnitPage");
const AdminHomePage=pick(()=>import("./DashboardPage"),"AdminHomePage"),AuditPage=pick(()=>import("./AuditPage"),"AuditPage");
const LoginPage=pick(()=>import("./AuthPages"),"LoginPage"),ForgotPasswordPage=pick(()=>import("./AuthPages"),"ForgotPasswordPage"),ResetPasswordPage=pick(()=>import("./AuthPages"),"ResetPasswordPage"),ChangePasswordPage=pick(()=>import("./AuthPages"),"ChangePasswordPage");

function AdminRoute({children}:{children:React.ReactNode}){return <ProtectedRoute roles={["ADMIN","SUPERADMIN","ADMIN_VICEMINISTERIO"]}><ManagementLayout area="admin">{children}</ManagementLayout></ProtectedRoute>}
function UnitRoute({children}:{children:React.ReactNode}){return <ProtectedRoute roles={["PRODUCTIVE_UNIT_RESPONSIBLE","EXPOSITOR"]}><ManagementLayout area="productive-unit">{children}</ManagementLayout></ProtectedRoute>}
function RouteMetadata(){const {pathname}=useLocation();useEffect(()=>{const title=pathname.startsWith("/admin")?"Administración":pathname.startsWith("/unidad-productiva")?"Unidad Productiva":pathname==="/solicitud-registro"?"Solicitud de registro":"Ferias activas";document.title=`${title} | Ferias Productivas Bolivia`;},[pathname]);return null}

export default function App(){return <><RouteMetadata/><Suspense fallback={<Loading label="Cargando página…"/>}><Routes>
  <Route path="/" element={<Navigate to="/catalogo" replace/>}/><Route path="/catalogo" element={<PublicCatalogPage/>}/><Route path="/catalogo/ferias/:fairId" element={<PublicFairPage/>}/><Route path="/catalogo/ferias/:fairId/unidades/:unitId" element={<PublicUnitPage/>}/><Route path="/solicitud-registro" element={<RegistrationPage/>}/>
  <Route path="/login" element={<LoginPage/>}/><Route path="/olvide-contrasena" element={<ForgotPasswordPage/>}/><Route path="/restablecer-contrasena" element={<ResetPasswordPage/>}/><Route path="/cambiar-contrasena" element={<ProtectedRoute><ChangePasswordPage/></ProtectedRoute>}/>
  <Route path="/admin" element={<AdminRoute><AdminHomePage/></AdminRoute>}/><Route path="/admin/solicitudes" element={<AdminRoute><RegistrationRequestsPage/></AdminRoute>}/><Route path="/admin/unidades-productivas" element={<AdminRoute><ProductiveUnitsPage/></AdminRoute>}/><Route path="/admin/sectores-productivos" element={<AdminRoute><ProductiveSectorsPage/></AdminRoute>}/><Route path="/admin/productos" element={<AdminRoute><AdminProductsPage/></AdminRoute>}/><Route path="/admin/ferias" element={<AdminRoute><FairsPage/></AdminRoute>}/><Route path="/admin/auditoria" element={<AdminRoute><AuditPage/></AdminRoute>}/>
  <Route path="/unidad-productiva" element={<Navigate to="/unidad-productiva/productos" replace/>}/><Route path="/unidad-productiva/perfil" element={<UnitRoute><ProductiveUnitProfilePage/></UnitRoute>}/><Route path="/unidad-productiva/sectores" element={<UnitRoute><UnitSectorsPage/></UnitRoute>}/><Route path="/unidad-productiva/productos" element={<UnitRoute><ProductsPage/></UnitRoute>}/>
  <Route path="/gestion/login" element={<Navigate to="/login" replace/>}/><Route path="/gestion/recuperar-contrasena" element={<Navigate to="/olvide-contrasena" replace/>}/><Route path="/gestion/restablecer-contrasena" element={<Navigate to="/restablecer-contrasena" replace/>}/><Route path="/gestion/cambiar-contrasena" element={<Navigate to="/cambiar-contrasena" replace/>}/><Route path="/gestion/admin/*" element={<Navigate to="/admin" replace/>}/><Route path="/gestion/expositor/*" element={<Navigate to="/unidad-productiva" replace/>}/>
  <Route path="*" element={<NotFoundPage/>}/>
</Routes></Suspense></>}
