import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ProjectNewPage from './pages/ProjectNewPage'
import InputPage from './pages/InputPage'
import ProcessSelectionPage from './pages/ProcessSelectionPage'
import CalculationPage from './pages/CalculationPage'
import EquipmentPage from './pages/EquipmentPage'
import DrawingUploadPage from './pages/DrawingUploadPage'
import DrawingMappingPage from './pages/DrawingMappingPage'
import VerificationPage from './pages/VerificationPage'
import ReportPage from './pages/ReportPage'
import SchemeWizardPage from './pages/SchemeWizardPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects/new" element={<ProjectNewPage />} />
          <Route path="/projects/:id" element={<InputPage />} />
          <Route path="/projects/:id/scheme" element={<SchemeWizardPage />} />
          <Route path="/projects/:id/process" element={<ProcessSelectionPage />} />
          <Route path="/projects/:id/calculation" element={<CalculationPage />} />
          <Route path="/projects/:id/drawings" element={<DrawingUploadPage />} />
          <Route path="/projects/:id/mapping" element={<DrawingMappingPage />} />
          <Route path="/projects/:id/verification" element={<VerificationPage />} />
          <Route path="/projects/:id/equipment" element={<EquipmentPage />} />
          <Route path="/projects/:id/report" element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
