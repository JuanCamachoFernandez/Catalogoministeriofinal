import { useEffect, useState } from 'react';
import { Eye, EyeOff, LogOut, ShieldCheck, Store } from 'lucide-react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api } from './api';
import { dashboardFor, isStrongPassword, type UserRole } from './authUtils';

type SessionUser={id:string;username:string;email:string;first_name:string;last_name:string;role:UserRole;must_change_password:boolean};

function PasswordField({label,value,onChange,autoComplete}:{label:string;value:string;onChange:(value:string)=>void;autoComplete:string}){
  const[visible,setVisible]=useState(false);
  return <label className="mt-4 block">{label}<span className="relative mt-2 block"><input required type={visible?'text':'password'} autoComplete={autoComplete} className="input pr-12" value={value} onChange={e=>onChange(e.target.value)}/><button type="button" onClick={()=>setVisible(v=>!v)} className="absolute inset-y-0 right-0 grid w-12 place-items-center text-muted" aria-label={visible?'Ocultar contraseña':'Mostrar contraseña'}>{visible?<EyeOff size={21}/>:<Eye size={21}/>}</button></span></label>;
}

export function LoginPage(){
  const navigate=useNavigate();const[login,setLogin]=useState('');const[password,setPassword]=useState('');const[message,setMessage]=useState('');
  const submit=async(e:React.FormEvent)=>{e.preventDefault();setMessage('');try{const r=await api.post('/auth/login',{login,password});const user:SessionUser=r.data.user;localStorage.setItem('token',r.data.access_token);localStorage.setItem('user',JSON.stringify(user));navigate(user.must_change_password?'/gestion/cambiar-contrasena':dashboardFor(user.role),{replace:true})}catch{setMessage('Credenciales inválidas.')}};
  return <main className="grid min-h-screen place-items-center bg-primary p-5"><form onSubmit={submit} className="card w-full max-w-md"><h1 className="text-2xl font-bold">Portal de gestión</h1><label className="mt-5 block">Usuario o Gmail<input required autoComplete="username" className="input mt-2" value={login} onChange={e=>setLogin(e.target.value)}/></label><PasswordField label="Contraseña" value={password} onChange={setPassword} autoComplete="current-password"/><button className="btn mt-6 w-full">Ingresar</button>{message&&<p className="mt-4 text-danger">{message}</p>}<Link className="mt-4 block text-center text-primary" to="/catalogo">Ir al catálogo público</Link></form></main>;
}

export function ChangePasswordPage(){
  const navigate=useNavigate();const[current,setCurrent]=useState('');const[next,setNext]=useState('');const[confirm,setConfirm]=useState('');const[message,setMessage]=useState('');
  if(!localStorage.getItem('token'))return <Navigate to="/gestion/login" replace/>;
  const submit=async(e:React.FormEvent)=>{e.preventDefault();setMessage('');if(next!==confirm){setMessage('Las contraseñas nuevas no coinciden.');return}if(!isStrongPassword(next)){setMessage('Use al menos 10 caracteres, una mayúscula, una minúscula, un número y un símbolo.');return}try{await api.post('/auth/change-password',{current_password:current,new_password:next});const user:SessionUser=JSON.parse(localStorage.getItem('user')??'null');if(!user)throw new Error('Sesión incompleta');user.must_change_password=false;localStorage.setItem('user',JSON.stringify(user));navigate(dashboardFor(user.role),{replace:true})}catch(error:any){setMessage(error.response?.data?.error??'No se pudo cambiar la contraseña.')}};
  return <main className="grid min-h-screen place-items-center bg-primary p-5"><form onSubmit={submit} className="card w-full max-w-lg"><p className="text-sm font-semibold uppercase tracking-wide text-primary">Primer ingreso</p><h1 className="mt-2 text-3xl font-bold">Cambie su contraseña</h1><p className="mt-3 text-muted">Debe reemplazar la contraseña temporal antes de acceder al sistema.</p><PasswordField label="Contraseña temporal actual" value={current} onChange={setCurrent} autoComplete="current-password"/><PasswordField label="Nueva contraseña" value={next} onChange={setNext} autoComplete="new-password"/><PasswordField label="Confirmar nueva contraseña" value={confirm} onChange={setConfirm} autoComplete="new-password"/><p className="mt-3 text-sm text-muted">Mínimo 10 caracteres, con mayúscula, minúscula, número y símbolo.</p>{message&&<p className="mt-4 rounded-lg alert-danger">{message}</p>}<button className="btn mt-6 w-full">Guardar nueva contraseña</button><button type="button" className="mt-3 w-full text-sm text-muted" onClick={()=>{localStorage.clear();navigate('/gestion/login')}}>Cerrar sesión</button></form></main>;
}

export function DashboardPage({area}:{area:'admin'|'expositor'}){
  const navigate=useNavigate();const[user,setUser]=useState<SessionUser|null>(()=>{try{return JSON.parse(localStorage.getItem('user')??'null')}catch{return null}});const[checking,setChecking]=useState(true);
  useEffect(()=>{api.get<SessionUser>('/auth/me').then(({data})=>{localStorage.setItem('user',JSON.stringify(data));setUser(data);if(data.must_change_password)navigate('/gestion/cambiar-contrasena',{replace:true});else if(area==='admin'&&data.role==='EXPOSITOR')navigate('/gestion/expositor/dashboard',{replace:true});else if(area==='expositor'&&data.role!=='EXPOSITOR')navigate('/gestion/admin/dashboard',{replace:true})}).catch(()=>{localStorage.clear();navigate('/gestion/login',{replace:true})}).finally(()=>setChecking(false))},[area,navigate]);
  if(!localStorage.getItem('token'))return <Navigate to="/gestion/login" replace/>;
  if(checking||!user)return <main className="grid min-h-screen place-items-center"><p>Verificando sesión…</p></main>;
  const isAdmin=user.role!=='EXPOSITOR';
  return <main className="min-h-screen bg-background"><header className="bg-primary text-surface"><div className="mx-auto flex max-w-6xl items-center justify-between p-5"><strong>Catálogo Digital de Ferias</strong><button className="flex items-center gap-2" onClick={()=>{localStorage.clear();navigate('/gestion/login',{replace:true})}}><LogOut size={18}/>Cerrar sesión</button></div></header><section className="mx-auto max-w-6xl p-6"><div className="card"><div className="flex items-center gap-3 text-primary">{isAdmin?<ShieldCheck size={32}/>:<Store size={32}/>}<p className="font-semibold">{isAdmin?'Panel administrativo':'Panel del expositor'}</p></div><h1 className="mt-4 text-3xl font-bold">Bienvenido, {user.first_name} {user.last_name}</h1><p className="mt-2 text-muted">Ingresó como {user.role.replaceAll('_',' ')}.</p><p className="mt-6 rounded-xl alert-warning">La sesión está activa. Los módulos administrativos completos todavía están en desarrollo.</p><Link to="/catalogo" className="btn mt-6">Ver catálogo público</Link></div></section></main>;
}
