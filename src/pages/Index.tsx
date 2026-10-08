import { Hero } from "@/components/Hero";
import { Problems } from "@/components/Problems";
import { Benefits } from "@/components/Benefits";
import { Features } from "@/components/Features";
import { TargetAudience } from "@/components/TargetAudience";
import { Contact } from "@/components/Contact";
import { Footer } from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Hero />
      <Problems />
      <Benefits />
      <Features />
      <TargetAudience />
      <Contact />
      <Footer />
    </div>
  );
};

export default Index;

