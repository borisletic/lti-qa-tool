# skip_delayed_jobs_in_migrations.rb
#
# Override send_later_if_production_enqueue_args da radi synchronously
# umesto enqueue-a delayed jobs. Ovo je potrebno za db:migrate na
# clean bazi jer delayed_jobs.max_concurrent kolona ne postoji do
# migracije 20150807133223 (AddMaxConcurrentToJobs), ali mnogo
# migracija pre toga pokušava enqueue delayed jobs.
#
# Na clean bazi nema data, pa su sve DataFixup metode no-op anyway.
# Ovo je safe za initial setup.

module SendLaterIfProductionPatch
  def send_later_if_production_enqueue_args(method_name, enqueue_args = {}, *args)
    # Direktno pozivi metodu synchronously — ne enqueue delayed job
    send(method_name, *args)
  end
end

# Patch na Object nivo jer Canvas ga koristi na raznim modelima
Object.prepend(SendLaterIfProductionPatch)
