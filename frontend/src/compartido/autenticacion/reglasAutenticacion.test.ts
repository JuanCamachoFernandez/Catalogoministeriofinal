import{describe,expect,it}from'vitest';
import { inicioParaRol } from "./roles";
import { esContrasenaSegura } from "../validaciones/contrasena";

describe('reglas de autenticación',()=>{
  it('envía administradores al panel administrativo',()=>{
    expect(inicioParaRol('SUPERADMIN')).toBe('/admin');
    expect(inicioParaRol('ADMIN_VICEMINISTERIO')).toBe('/admin');
    expect(inicioParaRol('ADMIN')).toBe('/admin');
  });
  it('envía expositores a su panel',()=>{
    expect(inicioParaRol('EXPOSITOR')).toBe('/unidad-productiva/productos');
    expect(inicioParaRol('PRODUCTIVE_UNIT_RESPONSIBLE')).toBe('/unidad-productiva/productos');
  });
  it('valida todos los requisitos de contraseña',()=>{
    expect(esContrasenaSegura('Segura2026!')).toBe(true);
    expect(esContrasenaSegura('sinSimbolo2026')).toBe(false);
    expect(esContrasenaSegura('Corta1!')).toBe(false);
  });
});
