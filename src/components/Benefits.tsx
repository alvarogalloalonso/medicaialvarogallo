import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, Zap, TrendingUp, Heart, Shield, Clock } from "lucide-react";

const benefits = [
  {icon: Zap, title: "Conversación", description: "Adaptadores para proveedores locales y externos; comportamiento pendiente de evaluación."},
  {icon: TrendingUp, title: "Clasificación experimental", description: "Router Naive Bayes y modelos XGBoost por especialidad; sin rendimiento clínico demostrado."},
  {icon: CheckCircle2, title: "Datos estructurados", description: "Síntomas confirmados, negados y no preguntados se representan por separado."},
  {icon: Heart, title: "Demo ficticia", description: "Casos fijos reproducibles sin descargar modelos ni contactar servicios de IA."},
  {icon: Shield, title: "Limitaciones visibles", description: "El sistema identifica los modelos ausentes y evita presentar predicciones inexistentes."},
  {icon: Clock, title: "Trabajo pendiente", description: "Datos con origen documentado, evaluación independiente y seguimiento de casos."}
];

export const Benefits = () => {
  return (
    <section className="py-20 bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Qué explora el proyecto
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Experimentos de software e integración de ML, sin beneficios clínicos demostrados
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {benefits.map((benefit, index) => (
            <Card key={index} className="border-border/50 bg-gradient-to-br from-card to-accent/20 hover:shadow-xl transition-all duration-300 group">
              <CardContent className="p-6">
                <div className="mb-4 inline-flex p-3 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 group-hover:from-primary/30 group-hover:to-secondary/30 transition-all">
                  <benefit.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground mb-2">{benefit.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{benefit.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

