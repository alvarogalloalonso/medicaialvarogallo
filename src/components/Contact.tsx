import { Card, CardContent } from "@/components/ui/card";
export const Contact = () => (
  <section className="py-20 bg-background">
    <div className="container mx-auto max-w-4xl">
      <Card><CardContent className="p-8 space-y-4">
        <h2 className="text-3xl font-bold">Explorar Medic AI</h2>
        <p>Proyecto independiente de Álvaro Gallo Alonso. La demo local y las instrucciones están disponibles en GitHub.</p>
        <a className="text-primary underline" href="https://github.com/alvarogalloalonso/medicaialvarogallo">Código, arquitectura y limitaciones</a>
        <p className="text-sm text-muted-foreground">Prototipo experimental. No se ofrece un servicio médico ni un formulario de recogida de datos.</p>
      </CardContent></Card>
    </div>
  </section>
);
