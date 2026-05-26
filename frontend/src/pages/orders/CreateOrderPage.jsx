import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import Button from '../../components/ui/Button'
import { toast } from 'sonner'

export default function CreateOrderPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  
  const [formData, setFormData] = useState({
    customer_id: '',
    commodity_name: '',
    quantity_kg: '',
    destination_country: '',
    agreed_price: '',
    currency: 'USD'
  })

  const handleChange = (e) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    // Simulate API call
    setTimeout(() => {
      setLoading(false)
      toast.success('Order created successfully')
      navigate('/orders')
    }, 1000)
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/orders')}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-beige-200 text-gray-500 transition-colors shrink-0"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="font-heading font-bold text-xl text-gray-900">Create New Order</h1>
          <p className="text-sm text-gray-500 font-body">Initialize a new shipment and its tracking pipeline.</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-beige-200 shadow-card p-6 space-y-6">
        
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-800 font-heading border-b border-beige-100 pb-2">Order Details</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Customer</label>
              <select 
                name="customer_id" 
                value={formData.customer_id} 
                onChange={handleChange}
                required
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              >
                <option value="">Select a customer...</option>
                <option value="1">Acme Spices LLC</option>
                <option value="2">Spice World GmbH</option>
                <option value="3">Gulf Flavors Co.</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Commodity Name</label>
              <input 
                type="text" 
                name="commodity_name" 
                value={formData.commodity_name} 
                onChange={handleChange}
                required
                placeholder="e.g. Turmeric Powder, Whole Black Pepper"
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Quantity (KG)</label>
              <input 
                type="number" 
                name="quantity_kg" 
                value={formData.quantity_kg} 
                onChange={handleChange}
                required
                min="1"
                placeholder="e.g. 5000"
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Destination Country</label>
              <input 
                type="text" 
                name="destination_country" 
                value={formData.destination_country} 
                onChange={handleChange}
                required
                placeholder="e.g. Germany"
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Agreed Price</label>
              <input 
                type="number" 
                name="agreed_price" 
                value={formData.agreed_price} 
                onChange={handleChange}
                step="0.01"
                min="0"
                placeholder="0.00"
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Currency</label>
              <select 
                name="currency" 
                value={formData.currency} 
                onChange={handleChange}
                className="w-full px-3 py-2.5 bg-white border border-beige-300 rounded-lg text-sm text-gray-900 outline-none focus:ring-2 focus:ring-saffron-500 font-body"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="INR">INR (₹)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Note */}
        <div className="bg-saffron-50 border border-saffron-100 rounded-lg p-3">
          <p className="text-xs text-saffron-800 font-body">
            <strong>Note:</strong> Creating this order will automatically initialize the 9-stage tracking pipeline for this shipment.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-beige-100">
          <Button type="button" variant="ghost" onClick={() => navigate('/orders')}>
            Cancel
          </Button>
          <Button type="submit" icon={Save} loading={loading}>
            Create Order
          </Button>
        </div>
      </form>
    </div>
  )
}
