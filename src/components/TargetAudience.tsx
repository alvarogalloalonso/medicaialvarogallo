import { Card, CardContent } from "@/components/ui/card";
import { User, Stethoscope, Building2, Shield } from "lucide-react";

const audiences = [
  {
    icon: User,
    title: "Pacientes",
    description: "Perspectiva inicial de diseño; no habilitado para uso con pacientes",
    color: "from-blue-500 to-cyan-500"
  },
  {
    icon: Stethoscope,
    title: "Profesionales Médicos",
    description: "Perspectiva inicial para presentar información estructurada",
    color: "from-green-500 to-emerald-500"
  },
  {
    icon: Building2,
    title: "Sistemas de Salud Públicos",
    description: "Contexto del problema explorado; impacto no medido",
    color: "from-purple-500 to-pink-500"
  },
  {
    icon: Shield,
    title: "Aseguradoras Privadas",
    description: "Posible contexto futuro; sin integración implementada",
    color: "from-orange-500 to-red-500"
  }
];

export const TargetAudience = () => {
  return (
    <section className="py-20 bg-gradient-to-b from-muted/30 to-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Contexto de la idea original
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Escenarios que motivaron la idea; esta versión se limita a demostraciones educativas
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {audiences.map((audience, index) => (
            <Card key={index} className="border-border/50 hover:shadow-xl transition-all duration-300 overflow-hidden group">
              <div className={`h-2 bg-gradient-to-r ${audience.color}`} />
              <CardContent className="p-6 text-center">
                <div className="mb-4 inline-flex p-4 rounded-full bg-muted/50 group-hover:scale-110 transition-transform">
                  <audience.icon className="h-8 w-8 text-foreground" />
                </div>
                <h3 className="font-semibold text-foreground mb-2 text-lg">{audience.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{audience.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

