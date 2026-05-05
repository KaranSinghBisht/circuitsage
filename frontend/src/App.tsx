import { Redirect, Route, Switch } from "wouter";
import { Home } from "./routes/Home";
import { Studio } from "./routes/Studio";
import { Bench } from "./routes/Bench";
import { Companion } from "./routes/Companion";
import { Educator } from "./routes/Educator";
import { Faults } from "./routes/Faults";
import { Uncertainty } from "./routes/Uncertainty";
import { AccessibilityProvider } from "./hooks/useA11yPrefs";

export default function App() {
  return (
    <AccessibilityProvider>
      <Switch>
        <Route path="/" component={Home} />
        <Route path="/studio/:id">{({ id }) => <Studio sessionId={id} />}</Route>
        <Route path="/bench/:id">{({ id }) => <Bench sessionId={id} />}</Route>
        <Route path="/companion" component={Companion} />
        <Route path="/educator" component={Educator} />
        <Route path="/faults" component={Faults} />
        <Route path="/uncertainty" component={Uncertainty} />
        <Route><Redirect to="/" /></Route>
      </Switch>
    </AccessibilityProvider>
  );
}
