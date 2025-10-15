# Arquitectura del Frontend - Plataforma Educativa Docker

Este documento describe la arquitectura del frontend de la plataforma educativa sobre Docker. 
El frontend está desarrollado en Next.js con TypeScript, utilizando TailwindCSS y shadcn/ui para la interfaz. 
La aplicación permitirá a los usuarios navegar por guías libremente y visualizar su contenido, pero requerirá 
autenticación para realizar ejercicios, registrar intentos y acceder a funcionalidades de cuenta.

## 1. Objetivo General

El frontend tiene como objetivo proveer una interfaz clara y responsiva para estudiantes y administradores. 
El usuario podrá consultar guías sin autenticación, pero necesitará iniciar sesión para resolver ejercicios, 
guardar intentos y ver su progreso. Las guías y ejercicios mostrarán un icono de completado cuando el usuario 
haya finalizado sus actividades, sin bloquear el acceso a nuevos contenidos.

## 2. Stack Tecnológico

| Área            | Tecnología                               |
|-----------------|------------------------------------------|
| Framework       | Next.js 15 (App Router)                  |
| Lenguaje        | TypeScript                               |
| UI              | TailwindCSS + shadcn/ui                  |
| Estado Global   | Zustand                                  |
| Autenticación   | Supabase Auth con persistencia en cookies|
| Animaciones     | Framer Motion                            |
| Renderizado     | react-markdown, react-html-parser        |
| Editor de Código| Monaco Editor o React Ace                |

## 3. Módulos del Frontend

- **Auth**: Manejo de login y registro con Supabase Auth. Persistencia en cookies. Solo autenticados pueden enviar intentos o registrar progreso.  
- **Guides**: Listado y detalle de guías (contenido HTML/Markdown). Acceso libre sin autenticación. Mostrar icono de completado.  
- **Exercises**: Listado y detalle de ejercicios por guía. Vista con enunciado y editor de código. Requiere autenticación para participar.  
- **Attempts**: Envío de respuestas, visualización de feedback del LLM y listado de intentos previos.  
- **Progress**: Mostrar iconos de ejercicios y guías completadas por el usuario.  
- **Admin**: CRUD de guías y ejercicios con formularios y editores enriquecidos (acceso restringido a administradores).  

## 4. Arquitectura de Carpetas Recomendada

```bash
frontend/
│── app/
│   ├── layout.tsx              # Layout general
│   ├── page.tsx                # Landing
│   ├── guides/
│   │   ├── page.tsx            # Listado de guías
│   │   └── [guideId]/page.tsx  # Detalle de guía + ejercicios
│   ├── exercises/
│   │   └── [exerciseId]/page.tsx  # Detalle de ejercicio
│   ├── admin/
│   │   ├── guides/page.tsx     # CRUD guías
│   │   └── exercises/page.tsx  # CRUD ejercicios
│   └── auth/
│       ├── login/page.tsx
│       └── register/page.tsx
│
│── components/
│   ├── ui/                     # Botones, modales, inputs (shadcn)
│   ├── layout/                 # Navbar, Sidebar, Footer
│   ├── guides/                 # Card guía, lista de guías
│   ├── exercises/              # Editor de código, feedback viewer
│   └── auth/                   # Formularios login/register
│
│── hooks/                      # Custom hooks
│── store/                      # Zustand (estado global)
│── services/                   # API Clients (fetch)
│── utils/                      # Funciones auxiliares
│── styles/                     # Estilos globales
```

## 5. Flujo de Navegación

- El usuario accede a la aplicación y puede explorar guías sin autenticarse.
- En el detalle de una guía, puede leer el contenido y ver los ejercicios asociados.
- Si intenta resolver un ejercicio o enviar una respuesta, se le pedirá autenticarse.
- Al completar ejercicios, se muestra un icono de completado. Si todos los ejercicios de una guía están completados, la guía también se marca con icono de completada.
- El usuario autenticado puede ver sus intentos previos y feedback del LLM. 
- Un administrador accede a /admin para gestionar guías y ejercicios.

## 6. Buenas Prácticas

- Mantener componentes reutilizables con shadcn/ui.
- Uso de Zustand para manejar estado global simple.
- React Query o SWR para caching de datos desde el backend.
- Render seguro de contenido HTML y Markdown.
- Implementar Monaco Editor o similar para los ejercicios.
- Diseño responsive optimizado para móviles.
- Persistencia de sesión en cookies para mayor seguridad.
