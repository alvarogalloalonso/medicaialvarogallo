import { Button } from "@/components/ui/button";
import { Mic, Sparkles, Square } from "lucide-react";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";

export const Hero = () => {
  const audioEnabled = import.meta.env.VITE_ENABLE_AUDIO === "true";
  const { isRecording, transcription, isTranscribing, toggleRecording } = useAudioRecorder();
  
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden bg-gradient-to-br from-accent via-background to-accent/50">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-4xl mx-auto text-center space-y-8 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-4">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Proyecto independiente · prototipo experimental</span>
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground">
            Sistema Inteligente de{" "}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Triaje Médico
            </span>{" "}
            Basado en IA
          </h1>
          
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Exploración de conversación con IA, extracción estructurada de síntomas e integración de modelos.
            Sin validación clínica. Utiliza únicamente ejemplos ficticios. La demo Python es una aplicación separada.
          </p>
          
          <div className="flex flex-col items-center gap-4 pt-4">
            <Button 
              size="lg" 
              className="group"
              onClick={toggleRecording}
              variant={isRecording ? "destructive" : "default"}
              disabled={isTranscribing || !audioEnabled}
            >
              {isRecording ? (
                <>
                  <Square className="h-5 w-5" />
                </>
              ) : isTranscribing ? (
                <>
                  <Sparkles className="h-5 w-5 animate-spin" />
                </>
              ) : (
                <>
                  <Mic className="h-5 w-5" />
                </>
              )}
            </Button>

            <p className="text-sm text-muted-foreground">La transcripción externa está desactivada por defecto. La demo offline está en local-prototype/.</p>
            {transcription && (
              <div className="mt-4 p-4 bg-card rounded-lg border border-border max-w-2xl">
                <h3 className="text-sm font-semibold text-foreground mb-2">Transcripción:</h3>
                <p className="text-sm text-muted-foreground">{transcription}</p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-background to-transparent" />
    </section>
  );
};

