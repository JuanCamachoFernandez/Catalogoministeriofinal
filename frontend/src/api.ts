import axios from 'axios';
export const api=axios.create({baseURL:import.meta.env.VITE_API_URL??'http://localhost:5000/api'});
api.interceptors.request.use(c=>{const t=localStorage.getItem('token');if(t)c.headers.Authorization=`Bearer ${t}`;return c});
export type Product={id:string;exhibitor_id:string;nombre:string;descripcion:string;estado:'AVAILABLE'|'OUT_OF_STOCK';imagenes:{url:string;is_cover:boolean}[]};
export type Fair={id:string;nombre:string;slug:string;descripcion:string;lugar:string;departamento:string;municipio:string;fecha_inicio:string;fecha_fin:string;imagen_portada:string};
