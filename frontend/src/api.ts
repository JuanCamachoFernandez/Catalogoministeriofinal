import axios from 'axios';
export const api=axios.create({baseURL:import.meta.env.VITE_API_URL??'http://localhost:5000/api'});
api.interceptors.request.use(c=>{const t=localStorage.getItem('token');if(t)c.headers.Authorization=`Bearer ${t}`;return c});
export type Product={id:string;exhibitor_id:string;category_id:string;nombre:string;slug:string;descripcion:string;materiales_o_ingredientes?:string|null;lugar_origen?:string|null;presentacion?:string|null;informacion_adicional?:string|null;precio:number|null;estado:'AVAILABLE'|'OUT_OF_STOCK'|'INACTIVE'|'DELETED';destacado:boolean;imagenes:{id?:string;url:string;is_cover:boolean;display_order?:number}[]};
export type Fair={id:string;nombre:string;slug:string;descripcion:string|null;lugar:string;direccion?:string|null;departamento:string;municipio:string;fecha_inicio:string;fecha_fin:string;imagen_portada:string;estado:string;visible_publicamente?:boolean};
export type Exhibitor={id:string;nombre_comercial:string;nombre_responsable:string;apellido_responsable:string;telefono_whatsapp:string;correo:string;departamento:string;municipio:string;estado:string;descripcion?:string|null;logo?:string|null};
export type Category={id:string;nombre:string;slug?:string;estado?:boolean};
