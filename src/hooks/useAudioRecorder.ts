import { useState, useRef } from 'react';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';

export const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState<string>('');
  const [transcription, setTranscription] = useState<string>('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const { toast } = useToast();

  const startRecording = async () => {
    try {
      if (import.meta.env.VITE_ENABLE_AUDIO !== "true") throw new Error("Audio desactivado en la demo");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: 'audio/webm;codecs=opus' } as MediaRecorderOptions;
      const mediaRecorder = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);
        
        stream.getTracks().forEach(track => track.stop());
        
        // Transcribir el audio
        setIsTranscribing(true);
        try {
          // Convertir blob a base64
          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = async () => {
            const base64Audio = (reader.result as string).split(',')[1];
            

            const localEndpoint = (import.meta as any).env?.VITE_TRANSCRIBE_ENDPOINT;
            if (localEndpoint) {
              try {
                const form = new FormData();
                form.append('file', audioBlob, 'audio.webm');
                const resp = await fetch(localEndpoint, { method: 'POST', body: form });
                if (!resp.ok) {
                  const errText = await resp.text();
                  throw new Error(errText || 'Local transcriber error');
                }
                const json = await resp.json();
                setTranscription(json.text || '');
                toast({ title: "Transcripción (local)", description: "Audio transcrito en tu equipo" });
                setIsTranscribing(false);
                return;
              } catch (e) {
                toast({title: 'Error de transcripción local', description: 'No se enviará audio a otro proveedor.', variant: 'destructive'});
                setIsTranscribing(false);
                return;
              }
            }

            if (!supabase) {
              toast({title: 'Servicio no configurado', description: 'Configura Supabase y una sesión autenticada para este experimento.', variant: 'destructive'});
              setIsTranscribing(false);
              return;
            }
            const { data, error } = await supabase.functions.invoke('transcribe-audio', {
              body: { audio: base64Audio }
            });

            if (error) {
              console.error('Error transcribiendo:', error);
              const serverMsg = (error as any)?.message || (error as any)?.toString?.() || 'No se pudo transcribir el audio';
              const isNoSpeech = serverMsg.toLowerCase().includes('no-speech');
              toast({
                title: isNoSpeech ? 'Sin voz detectada' : 'Error',
                description: isNoSpeech ? 'No se detectó voz. Mantén pulsado 2–3s, habla claro y revisa permisos del micrófono.' : serverMsg,
                variant: 'destructive',
              });
            } else {
              setTranscription(data.text);
              toast({
                title: "Transcripción completada",
                description: "Audio transcrito correctamente",
              });
            }
            setIsTranscribing(false);
          };
        } catch (error) {
          console.error('Error al transcribir:', error);
          toast({
            title: "Error",
            description: "No se pudo transcribir el audio",
            variant: "destructive",
          });
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      
      toast({
        title: "Grabando...",
        description: "La grabación ha iniciado",
      });
    } catch (error) {
      console.error('Error al acceder al micrófono:', error);
      toast({
        title: "Error",
        description: "No se pudo acceder al micrófono",
        variant: "destructive",
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return {
    isRecording,
    audioURL,
    transcription,
    isTranscribing,
    toggleRecording,
    startRecording,
    stopRecording,
  };
};

