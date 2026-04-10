import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Cpu, LogIn } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const USERS = [
  "alejandro.barrera",
  "victoria.corroto",
  "marta.sanz",
  "carlo.villegas",
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState(USERS[0]);
  const [password, setPassword] = useState("123456");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await login(username, password);
      toast.success("Sesión iniciada");
    } catch {
      toast.error("Credenciales inválidas");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#fde6d6,_transparent_40%),linear-gradient(135deg,_#243444_0%,_#18222e_100%)] px-4 py-12">
      <div className="mx-auto flex max-w-5xl items-center gap-12">
        <div className="hidden flex-1 text-white lg:block">
          <img src="/logo.png" alt="qaracter" className="mb-6 h-12 w-auto" />
          <h1 className="max-w-xl text-4xl font-bold leading-tight">Predatadas con trazabilidad operativa y control de consumo IA.</h1>
          <p className="mt-4 max-w-lg text-sm leading-7 text-white/70">
            Accede con uno de los usuarios demo para validar conciliación de campos clave, analítica, reporting y consumo de modelos IA por usuario.
          </p>
        </div>

        <Card className="w-full max-w-md border-white/10 bg-white/95 shadow-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl text-zinc-900">
              <LogIn className="h-5 w-5 text-[#fc7c34]" />
              Iniciar sesión
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleLogin}>
              <div className="space-y-2">
                <Label>Usuario</Label>
                <Input value={username} onChange={(e) => setUsername(e.target.value)} list="demo-users" />
                <datalist id="demo-users">
                  {USERS.map((item) => (
                    <option key={item} value={item} />
                  ))}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label>Contraseña</Label>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Accediendo..." : "Entrar"}
              </Button>
            </form>

            <div className="mt-5 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
              <div className="mb-2 flex items-center gap-2 font-semibold text-zinc-800">
                <Cpu className="h-3.5 w-3.5 text-[#fc7c34]" />
                Usuarios demo
              </div>
              <ul className="space-y-1">
                {USERS.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="mt-2">Contraseña común: <strong>123456</strong></p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
