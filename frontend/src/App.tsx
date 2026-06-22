import { useEffect, useState } from "react";
import api from "./services/weatherApi"

function App() {
  const [message, setMessage] = useState("");

    useEffect(() => {
    api.get("/")
      .then((response) => {
        setMessage(response.data.message);
      });
  }, []);

  return (
    <div>
      <h1>{message}</h1>
    </div>
  );
}

export default App;