import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Clock, Users, FileText, TrendingDown, Stethoscope } from "lucide-react";

const problems = [
  {
    icon: Users,
    title: "Saturación de Consultas",
    description: "La organización de consultas motivó la exploración; no se ha probado una mejora con este proyecto."
  },
  {
    icon: Clock,
    title: "Pérdida de Tiempo",
    description: "Los médicos dedican tiempo valioso a entrevistas clínicas básicas que podrían automatizarse."
  },
  {
    icon: FileText,
    title: "Omisiones Involuntarias",
    description: "Síntomas importantes pueden pasarse por alto durante la recogida manual de información."
  },
  {
    icon: AlertCircle,
    title: "Retrasos en Urgencias",
    description: "Los casos verdaderamente urgentes no siempre reciben la prioridad que necesitan."
  },
  {
    icon: TrendingDown,
    title: "Listas de Espera Extensas",
    description: "Tiempos de espera prolongados dificultan el acceso oportuno a la atención médica."
  },
  {
    icon: Stethoscope,
    title: "Jornadas Excesivas",
    description: "Los profesionales médicos enfrentan jornadas largas por tareas repetitivas y administrativas."
  }
];

export const Problems = () => {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Problemas que motivaron la idea
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            El sistema de salud actual enfrenta múltiples desafíos que afectan tanto a pacientes como a profesionales
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {problems.map((problem, index) => (
            <Card key={index} className="border-border/50 hover:border-primary/50 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <problem.icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground mb-2">{problem.title}</h3>
                    <p className="text-sm text-muted-foreground">{problem.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

