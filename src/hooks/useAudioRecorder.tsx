import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Mic, Square, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const AudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(true);
  
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    // Check if browser supports Web Speech API
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setIsSupported(false);
      toast.error('Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.');
      return;
    }

    // Initialize speech recognition
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';

    recognition.onresult = (event: any) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript + ' ';
        } else {
          interim += transcript;
        }
      }

      if (final) {
        setTranscript(prev => prev + final);
        setInterimTranscript('');
      } else {
        setInterimTranscript(interim);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      if (event.error === 'not-allowed') {
        toast.error('Permiso de micrófono denegado');
      } else {
        toast.error('Error en el reconocimiento de voz');
      }
      setIsRecording(false);
    };

    recognition.onend = () => {
      if (isRecording) {
        recognition.start();
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [isRecording]);

  const startRecording = async () => {
    try {
      // Request microphone permission and start recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Start audio recording
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.start();

      // Start speech recognition
      if (recognitionRef.current) {
        recognitionRef.current.start();
      }

      setIsRecording(true);
      setTranscript('');
      setInterimTranscript('');
      toast.success('Grabación iniciada');
    } catch (error) {
      console.error('Error starting recording:', error);
      toast.error('No se pudo acceder al micrófono');
    }
  };

  const stopRecording = () => {
    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    // Stop audio recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }

    setIsRecording(false);
    toast.success('Grabación detenida');
  };

  if (!isSupported) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">
          Tu navegador no soporta reconocimiento de voz. Por favor, usa Chrome o Edge.
        </p>
      </Card>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card className="p-8 gradient-card shadow-lg">
        <div className="flex flex-col items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              {isRecording && (
                <div className="absolute inset-0 animate-pulse-glow rounded-full" />
              )}
              <Button
                onClick={startRecording}
                disabled={isRecording}
                size="lg"
                className="relative h-24 w-24 rounded-full transition-all duration-300 bg-primary hover:bg-primary/90 gradient-hero disabled:opacity-50"
              >
                <Mic className="h-10 w-10" />
              </Button>
            </div>

            {isRecording && (
              <Button
                onClick={stopRecording}
                size="lg"
                className="h-24 px-8 rounded-full bg-destructive hover:bg-destructive/90 transition-all duration-300"
              >
                <Square className="h-6 w-6 mr-2" />
                Finalizar Llamada
              </Button>
            )}
          </div>

          <div className="text-center space-y-2">
            <h3 className="text-xl font-semibold">
              {isRecording ? 'Grabando...' : 'Iniciar Llamada'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {isRecording 
                ? 'Hable claramente cerca del micrófono' 
                : 'Presione el botón para comenzar la grabación'}
            </p>
          </div>

          {isRecording && (
            <div className="flex items-center gap-2 text-destructive">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm font-medium">Escuchando...</span>
            </div>
          )}
        </div>
      </Card>

      {(transcript || interimTranscript) && (
        <Card className="p-6 gradient-card shadow-md">
          <h4 className="text-lg font-semibold mb-4">Transcripción:</h4>
          <div className="prose prose-sm max-w-none">
            <p className="text-foreground whitespace-pre-wrap leading-relaxed">
              {transcript}
              {interimTranscript && (
                <span className="text-muted-foreground italic">
                  {interimTranscript}
                </span>
              )}
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};

export default AudioRecorder;


