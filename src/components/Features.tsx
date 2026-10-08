import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Percent, Stethoscope, AlertCircle } from "lucide-react";

export const Features = () => {
  return (
    <section className="py-20 bg-gradient-to-br from-background via-accent/10 to-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Informe Inteligente de Triaje
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            El prototipo Python construye informes experimentales a partir de ejemplos ficticios. Esta web no está conectada a ese backend.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto mb-12">
          <Card className="border-border/50 bg-card hover:shadow-lg transition-all">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Percent className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Probabilidades Estimadas</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Los clasificadores usan síntomas estructurados. Sus salidas requieren entrenamiento reproducible y no son probabilidades clínicas validadas.
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card hover:shadow-lg transition-all">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Informe estructurado</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                El informe separa síntomas confirmados y negados, reglas experimentales y predicciones disponibles. La demo no genera recomendaciones diagnósticas mediante un LLM.
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="border-primary/30 bg-gradient-to-br from-card to-primary/5 max-w-4xl mx-auto">
          <CardContent className="p-8">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-lg bg-primary/10 shrink-0">
                <AlertCircle className="h-7 w-7 text-primary" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground mb-3 flex items-center gap-2">
                  <Stethoscope className="h-5 w-5 text-primary" />
                  Prototipo educativo
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  Este proyecto <strong>no está validado para uso médico</strong>. Demuestra técnicas de desarrollo
                  e integración de modelos. Usa únicamente datos ficticios; las funciones de seguimiento están pendientes.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
};

