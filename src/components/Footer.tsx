export const Footer = () => {
  return (
    <footer className="bg-muted/30 border-t border-border/50 py-12">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h3 className="text-2xl font-bold text-foreground mb-2">
            Sistema de Triaje Médico IA
          </h3>
          <p className="text-sm text-muted-foreground mb-6">
            Prototipo educativo de conversación, extracción e integración de ML
          </p>
          <div className="border-t border-border/50 pt-6">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} Álvaro Gallo Alonso. Todos los derechos reservados.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Proyecto en fase de diseño - Trabajo de Fin de Grado
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

