# OVERRIDE: no-op za development/test setup.
#
# Originalna migracija enqueue-uje delayed job koji popunjava
# submission_versions data. Ta migracija krcši na clean bazi jer
# Delayed::Backend::ActiveRecord::Job očekuje kolonu max_concurrent
# na delayed_jobs tabli — ali ta kolona se dodaje migracijom
# AddMaxConcurrentToJobs (20150807133223) koja dolazi znatno posle.
#
# Na fresh bazi nema submission data, pa je no-op potpuno ispravno.

class PopulateSubmissionVersions < ActiveRecord::Migration[4.2]
  tag :postdeploy
  def up
    # intentionally empty - no submission data on fresh DB
  end

  def down
    # intentionally empty
  end
end
